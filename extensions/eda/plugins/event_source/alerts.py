"""Poll Edwin AI / LogicMonitor for new alerts.

Periodically queries the Edwin AI API for active alerts and emits
new or changed alerts as events. Tracks seen alerts to avoid
duplicate events.

Arguments:
    portal: Edwin AI portal name (e.g. 'mycompany')
    access_id: API access ID
    access_key: API access key
    interval: Polling interval in seconds (default: 60)
    severity: Minimum severity to emit (default: 'warning')
    resource_group: Optional resource group filter
"""

import asyncio
import logging
import re
from typing import Any

IMPORT_ERRORS = []
try:
    import requests
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

logger = logging.getLogger(__name__)

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
    min_severity = args.get("severity", "warning").lower()
    resource_group = args.get("resource_group", "")
    min_level = SEVERITY_LEVELS.get(min_severity, 2)

    seen_alerts: dict[str, str] = {}

    while True:
        try:
            token = _get_token(portal, access_id, access_key)
            alerts = _fetch_alerts(portal, token, resource_group)

            current_ids = set()
            for alert in alerts:
                alert_id = str(alert.get("id", ""))
                current_ids.add(alert_id)
                severity = alert.get(
                    "severity", alert.get("level", "info")
                ).lower()
                level = SEVERITY_LEVELS.get(severity, 1)

                if level < min_level:
                    continue

                status_key = f"{alert_id}:{alert.get('status', '')}"
                if seen_alerts.get(alert_id) == status_key:
                    continue
                seen_alerts[alert_id] = status_key

                event = _normalize_event(alert)
                await queue.put(event)

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


def _fetch_alerts(
    portal: str, token: str, resource_group: str = ""
) -> list[dict]:
    portal = _validate_portal(portal)
    url = f"https://{portal}.dexda.ai/api/v1/alerts"
    params: dict[str, Any] = {"status": "active", "size": 100}
    if resource_group:
        params["resourceGroup"] = resource_group

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
        verify=True,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("items", data.get("data", []))


def _normalize_event(alert: dict) -> dict:
    return {
        "edwin_ai": {
            "event_type": alert.get("type", "alert"),
            "alert_id": str(alert.get("id", "")),
            "severity": alert.get(
                "severity", alert.get("level", "unknown")
            ),
            "host": alert.get(
                "host",
                alert.get("resourceName", alert.get("device", "")),
            ),
            "message": alert.get(
                "message",
                alert.get("description", alert.get("summary", "")),
            ),
            "metric": alert.get("metric", alert.get("datapoint", "")),
            "value": alert.get("value", alert.get("currentValue", "")),
            "threshold": alert.get("threshold", ""),
            "resource_group": alert.get(
                "resourceGroup", alert.get("group", "")
            ),
            "timestamp": alert.get(
                "timestamp", alert.get("startEpoch", "")
            ),
            "status": alert.get(
                "status", alert.get("alertStatus", "active")
            ),
            "raw": alert,
        }
    }
