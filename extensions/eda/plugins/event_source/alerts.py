"""Poll Edwin AI / LogicMonitor for new alerts."""

DOCUMENTATION = r"""
---
short_description: Poll Edwin AI for alerts and emit them as events.
description:
    - Periodically queries the Edwin AI query API (the same C(/ui/query/records)
      endpoint used by the M(logicmonitor.edwin_ai.query_api) module) for recent
      alerts at or above a severity threshold, and emits new or changed alerts as
      events. Seen alerts are tracked to avoid duplicate events.
options:
    portal:
        description:
            - Edwin AI portal name (subdomain only, e.g. C(mycompany) for
              C(mycompany.dexda.ai)).
        type: str
        required: true
    access_id:
        description: API access ID.
        type: str
        required: true
    access_key:
        description: API access key.
        type: str
        required: true
    interval:
        description: Polling interval in seconds (minimum 10).
        type: int
        default: 60
    min_severity:
        description:
            - Minimum integer event severity to emit (C(cf.eventSeverity);
              higher is more severe). A severity name
              (C(critical)/C(error)/C(warning)/C(info)) is also accepted
              (case-insensitive) and mapped to an integer. Unknown names raise
              an error.
        type: raw
        default: 4
    lookback:
        description: Time window in seconds (ending now) to query (default: 86400, which is 1 day).
        type: int
        default: 86400
    size:
        description: Maximum number of records to request per poll.
        type: int
        default: 100
"""

EXAMPLES = r"""
- name: Poll Edwin AI for high-severity alerts
  hosts: all
  sources:
    - logicmonitor.edwin_ai.alerts:
        portal: "{{ EDWIN_PORTAL }}"
        access_id: "{{ EDWIN_ACCESS_ID }}"
        access_key: "{{ EDWIN_ACCESS_KEY }}"
        interval: 60
        min_severity: 4
        lookback: 86400
  rules:
    - name: High-severity alert
      condition: event.edwin_ai.severity >= 4 and event.edwin_ai.status == "active"
      action:
        debug:
"""

import asyncio
import logging
import time
from json import dumps
from typing import Any

from ansible_collections.logicmonitor.edwin_ai.plugins.module_utils._rest_methods import (
    get_auth_token,
    post,
    _validate_portal,
)
from ansible_collections.logicmonitor.edwin_ai.plugins.module_utils._query import (
    create_filter,
    create_order,
)

logger = logging.getLogger(__name__)

# Legacy severity-name -> integer mapping. The API uses an integer
# ``cf.eventSeverity`` (higher is more severe); names are accepted for
# convenience and mapped to a threshold.
SEVERITY_LEVELS = {
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4,
}


def _resolve_min_severity(value: Any) -> int:
    """Resolve a severity threshold from an integer or a known severity name.

    Raises ``ValueError`` for unknown names (so a typo is not silently treated
    as a default) and for negative values.
    """
    if isinstance(value, bool):
        raise ValueError(f"Invalid min_severity: {value!r}")
    if isinstance(value, int):
        severity = value
    else:
        text = str(value).strip().lower()
        if text.lstrip("-").isdigit():
            severity = int(text)
        elif text in SEVERITY_LEVELS:
            severity = SEVERITY_LEVELS[text]
        else:
            raise ValueError(
                f"Invalid min_severity: {value!r}. "
                f"Use a non-negative integer or one of {sorted(SEVERITY_LEVELS)}."
            )
    if severity < 0:
        raise ValueError(f"min_severity must be >= 0, got {severity}")
    return severity


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Poll Edwin AI for alerts and forward to the EDA rulebook."""
    portal = _validate_portal(args["portal"])
    access_id = args["access_id"]
    access_key = args["access_key"]

    interval = int(args.get("interval", 60))
    if interval < 10:
        raise ValueError("interval must be at least 10 seconds")
    min_severity = _resolve_min_severity(args.get("min_severity", 4))
    lookback = int(args.get("lookback", 86_400))
    if lookback <= 0:
        raise ValueError("lookback must be a positive number of seconds")
    size = int(args.get("size", 100))
    if size <= 0:
        raise ValueError("size must be a positive integer")

    # alert_id -> dedup key (state + last-update + severity); we re-emit only on change
    seen_alerts: dict[str, str] = {}

    while True:
        try:
            token = get_auth_token(portal, access_id, access_key)
            records = _fetch_alerts(portal, token, min_severity, lookback, size)

            current_ids = set()
            for record in records:
                alert_id = str(record.get("_id", ""))
                if not alert_id:
                    continue
                current_ids.add(alert_id)

                dedup_key = "{}:{}:{}".format(
                    record.get("alertDetails.alertState"),
                    record.get("meta.updatedTimestamp"),
                    record.get("cf.eventSeverity"),
                )
                if seen_alerts.get(alert_id) == dedup_key:
                    continue
                seen_alerts[alert_id] = dedup_key

                await queue.put(_normalize_event(record))

        except Exception:
            logger.exception("Error polling Edwin AI alerts")

        await asyncio.sleep(interval)


def _build_query(min_severity: int, lookback: int, size: int) -> dict:
    """Build the ``/ui/query/records`` request body (shares the query_api builders)."""
    start_epoch = int((time.time() - lookback) * 1_000)
    return {
        "env": {"timezone": "Europe/London"},
        "fields": [],
        "recordType": "alerts",
        "size": size,
        "filter": create_filter(
            "cf.eventSeverity", "meta.createdTimestamp", start_epoch, min_severity
        ),
        "order": create_order("meta.createdTimestamp"),
    }


def _fetch_alerts(
    portal: str, token: str, min_severity: int, lookback: int, size: int
) -> list[dict]:
    portal = _validate_portal(portal)
    url = f"https://{portal}.dexda.ai/ui/query/records"
    response = post(url, token, dumps(_build_query(min_severity, lookback, size)))
    response.raise_for_status()
    return response.json().get("results", [])


def _first(record: dict, *keys: str, default: Any = None) -> Any:
    """Return the first non-empty value among the given (dotted) record keys."""
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize_event(record: dict) -> dict:
    """Normalize an Edwin AI alert record to a consistent event schema.

    Records from ``/ui/query/records`` use flat, dotted string keys (e.g.
    ``cf.eventSeverity``). ``severity`` is the integer ``cf.eventSeverity``
    (higher is more severe); ``status`` is lower-cased; ``alert_id`` is left as
    the opaque unique record key. The full record is preserved under ``raw``.
    """
    status = record.get("alertDetails.alertState")
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
            "timestamp": record.get("meta.createdTimestamp"),
            "status": status.lower() if isinstance(status, str) else None,
            "link": _first(record, "meta.link"),
            "raw": record,
        }
    }
