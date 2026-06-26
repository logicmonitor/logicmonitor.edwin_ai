"""Poll Edwin AI / LogicMonitor for new alerts.

Periodically queries the Edwin AI query API (``/ui/query/records``, the same
endpoint used by the ``query_api`` module) for recent alerts at or above a
severity threshold and emits new or changed alerts as events. Tracks seen
alerts to avoid duplicate events.

Arguments:
    portal: Edwin AI portal name (e.g. 'mycompany' for mycompany.dexda.ai)
    access_id: API access ID
    access_key: API access key
    interval: Polling interval in seconds (default: 60, minimum: 10)
    min_severity: Minimum integer event severity to emit (``cf.eventSeverity``;
        default: 4 - higher is more severe). A legacy severity name
        ('critical'/'error'/'warning'/'info') is also accepted and mapped to an
        integer for backwards compatibility.
    lookback: Time window in seconds (ending now) to query (default: 86400).
    size: Maximum number of records to request per poll (default: 100).
"""

import asyncio
import logging
import re
import time
from typing import Any

IMPORT_ERRORS = []
try:
    import requests
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

logger = logging.getLogger(__name__)

# Legacy severity-name -> integer mapping. The API uses an integer
# ``cf.eventSeverity`` (higher is more severe), so names are only accepted for
# backwards compatibility and mapped to a threshold.
SEVERITY_LEVELS = {
    "critical": 4,
    "error": 3,
    "warning": 2,
    "info": 1,
}

_VALID_PORTAL = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")


def _validate_portal(portal: str) -> str:
    if not _VALID_PORTAL.match(portal):
        raise ValueError(
            f"Invalid portal name: {portal!r}. "
            "Must be alphanumeric with hyphens/dots/underscores."
        )
    return portal


def _resolve_min_severity(value: Any) -> int:
    """Accept an integer threshold or a legacy severity name."""
    if isinstance(value, bool):
        return 4
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text.isdigit():
        return int(text)
    return SEVERITY_LEVELS.get(text, 4)


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Poll Edwin AI for alerts and forward to the EDA rulebook."""
    for exc in IMPORT_ERRORS:
        raise exc

    portal = _validate_portal(args["portal"])
    access_id = args["access_id"]
    access_key = args["access_key"]
    interval = int(args.get("interval", 60))
    if interval < 10:
        raise ValueError("Polling interval must be at least 10 seconds")
    min_severity = _resolve_min_severity(
        args.get("min_severity", args.get("severity", 4))
    )
    lookback = int(args.get("lookback", 86_400))
    size = int(args.get("size", 100))

    # alert_id -> dedup key (state + last update), so we only re-emit on change
    seen_alerts: dict[str, str] = {}

    while True:
        try:
            token = _get_token(portal, access_id, access_key)
            records = _fetch_alerts(portal, token, min_severity, lookback, size)

            current_ids = set()
            for record in records:
                alert_id = str(record.get("_id", ""))
                if not alert_id:
                    continue
                current_ids.add(alert_id)

                state = str(record.get("alertDetails.alertState", "active"))
                updated = record.get("meta.updatedTimestamp", "")
                status_key = f"{alert_id}:{state}:{updated}"
                if seen_alerts.get(alert_id) == status_key:
                    continue
                seen_alerts[alert_id] = status_key

                await queue.put(_normalize_event(record))

            # Alerts that fell out of the result set are treated as cleared.
            # NOTE: because results are constrained by `lookback`, an alert can
            # also drop out simply by ageing past the window.
            cleared = set(seen_alerts.keys()) - current_ids
            for alert_id in cleared:
                await queue.put({
                    "edwin_ai": {
                        "event_type": "alert_cleared",
                        "alert_id": alert_id,
                        "status": "cleared",
                    }
                })
                del seen_alerts[alert_id]

        except Exception:
            logger.exception("Error polling Edwin AI alerts")

        await asyncio.sleep(interval)


def _get_token(portal: str, access_id: str, access_key: str) -> str:
    portal = _validate_portal(portal)
    response = requests.post(
        f"https://{portal}.dexda.ai/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": access_id,
            "client_secret": access_key,
        },
        timeout=30,
        verify=True,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _build_query(min_severity: int, lookback: int, size: int) -> dict:
    """Build the ``/ui/query/records`` request body (mirrors the query_api module)."""
    start_epoch = int((time.time() - lookback) * 1_000)
    return {
        "env": {"timezone": "Europe/London"},
        "fields": [],
        "recordType": "alerts",
        "size": size,
        "filter": {
            "expression": {
                "AND": [
                    {"GREATER_THAN_EQUAL": [
                        {"field": "cf.eventSeverity", "type": "integer"},
                        min_severity,
                    ]},
                    {"GREATER_THAN_EQUAL": [
                        {"field": "meta.createdTimestamp", "type": "long"},
                        start_epoch,
                    ]},
                ]
            },
            "schemaName": "filterCondition",
            "schemaVersion": "4",
        },
        "order": [{"type": "desc", "field": "meta.createdTimestamp"}],
    }


def _fetch_alerts(
    portal: str, token: str, min_severity: int, lookback: int, size: int
) -> list[dict]:
    portal = _validate_portal(portal)
    response = requests.post(
        f"https://{portal}.dexda.ai/ui/query/records",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=_build_query(min_severity, lookback, size),
        timeout=30,
        verify=True,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def _first(record: dict, *keys: str, default: Any = "") -> Any:
    """Return the first non-empty value among the given (dotted) record keys."""
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_event(record: dict) -> dict:
    """Normalize an Edwin AI alert record to a consistent event schema.

    Records from ``/ui/query/records`` use flat, dotted string keys (e.g.
    ``cf.eventSeverity``), so this reads those directly. ``severity`` is the
    integer ``cf.eventSeverity`` (higher is more severe). The full record is
    preserved under ``raw`` so rulebooks can access any field.
    """
    return {
        "edwin_ai": {
            "event_type": _first(record, "cf.eventType", default="alert"),
            "alert_id": _first(record, "_id", "meta.alertKey"),
            "severity": record.get("cf.eventSeverity", 0),
            "host": _first(record, "cf.eventCI", "cf.eventObject"),
            "message": _first(
                record, "cf.eventDescription", "cf.eventDetails", "cf.eventName"
            ),
            "metric": _first(record, "cf.eventName"),
            "event_source": _first(record, "cf.eventSource"),
            "resource_group": _first(record, "extra.itsm_assignment_group"),
            "timestamp": record.get("meta.createdTimestamp", ""),
            "status": _first(record, "alertDetails.alertState", default="active"),
            "link": _first(record, "meta.link"),
            "raw": record,
        }
    }
