"""Receive Edwin AI alert events via webhook."""

DOCUMENTATION = r"""
---
short_description: Receive Edwin AI alert events via an HTTP webhook.
description:
    - Starts an HTTP listener that receives alert notifications pushed by Edwin
      AI (or a compatible sender) and emits them as events. Configure the sender
      to POST to this listener's URL.
options:
    host:
        description: Bind address for the webhook listener.
        type: str
        default: "0.0.0.0"
    port:
        description: Port to listen on.
        type: int
        default: 5000
    token:
        description:
            - Optional shared secret for HMAC-SHA256 signature verification. When
              set, the request signature is validated against an HMAC of the raw
              body. The standard C(X-Hub-Signature-256) header is supported (value
              may be prefixed with C(sha256=)), as is the alternative
              C(X-Edwin-Signature) header (raw hex) for backward compatibility.
        type: str
        required: false
"""

EXAMPLES = r"""
- name: Receive Edwin AI alerts over a webhook
  hosts: all
  sources:
    - logicmonitor.edwin_ai.webhook:
        host: 0.0.0.0
        port: 5000
        token: "{{ EDWIN_WEBHOOK_SECRET }}"
  rules:
    - name: Critical alert
      condition: event.edwin_ai.severity == "critical"
      action:
        debug:
"""

import asyncio
import json
import hashlib
import hmac
import logging
import re
from typing import Any

IMPORT_ERRORS = []
try:
    from aiohttp import web
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

logger = logging.getLogger(__name__)

_VALID_HOST = re.compile(r"^[\d.a-fA-F:]+$")
_MAX_PAYLOAD_BYTES = 1_048_576


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Receive Edwin AI webhook events and forward to the EDA rulebook."""
    for exc in IMPORT_ERRORS:
        raise exc

    host = str(args.get("host", "0.0.0.0"))
    if not _VALID_HOST.match(host):
        raise ValueError(f"Invalid bind address: {host!r}")
    port = int(args.get("port", 5000))
    if not 1 <= port <= 65535:
        raise ValueError(f"Port must be between 1 and 65535, got {port}")
    token = args.get("token", "")

    app = web.Application(client_max_size=_MAX_PAYLOAD_BYTES)

    async def _handle_event(request: web.Request) -> web.Response:
        try:
            payload = await request.read()
            if len(payload) > _MAX_PAYLOAD_BYTES:
                return web.Response(status=413, text="Payload too large")

            if token:
                expected = hmac.new(
                    token.encode(), payload, hashlib.sha256
                ).hexdigest()
                if not _verify_signature(request.headers, expected):
                    logger.warning("Invalid webhook signature received")
                    return web.Response(status=401, text="Invalid signature")

            data = json.loads(payload)
            if not isinstance(data, dict):
                return web.Response(status=400, text="Invalid payload format")
            event = _normalize_event(data)
            await queue.put(event)
            return web.Response(status=200, text="OK")
        except json.JSONDecodeError:
            logger.error("Received invalid JSON payload")
            return web.Response(status=400, text="Invalid JSON")
        except web.HTTPException:
            raise
        except Exception:
            logger.exception("Error processing webhook event")
            return web.Response(status=500, text="Internal error")

    async def _health(request: web.Request) -> web.Response:
        return web.Response(status=200, text="OK")

    app.router.add_post("/", _handle_event)
    app.router.add_post("/webhook", _handle_event)
    app.router.add_get("/health", _health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Edwin AI webhook listener started on %s:%d", host, port)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


def _verify_signature(headers: Any, expected_hex: str) -> bool:
    """Validate an HMAC-SHA256 signature against the supported headers.

    Accepts the GitHub-standard ``X-Hub-Signature-256`` header (value may be
    prefixed with ``sha256=``) and the alternative ``X-Edwin-Signature`` header
    (raw hex). Comparison is timing-safe.
    """
    candidates = []

    hub = headers.get("X-Hub-Signature-256", "")
    if hub:
        prefix = "sha256="
        candidates.append(hub[len(prefix):] if hub.startswith(prefix) else hub)

    legacy = headers.get("X-Edwin-Signature", "")
    if legacy:
        candidates.append(legacy)

    return any(
        hmac.compare_digest(candidate, expected_hex) for candidate in candidates
    )


def _normalize_event(data: dict) -> dict:
    """Normalize Edwin AI webhook payload to a consistent event schema."""
    severity = data.get("severity", data.get("level", "unknown"))
    status = data.get("status", data.get("alertStatus", "active"))

    return {
        "edwin_ai": {
            "event_type": data.get("type", data.get("eventType", "alert")),
            "alert_id": data.get("alertId", data.get("id", "")),
            "severity": severity.lower() if isinstance(severity, str) else severity,
            "host": data.get(
                "host", data.get("resourceName", data.get("device", ""))
            ),
            "message": data.get(
                "message", data.get("description", data.get("summary", ""))
            ),
            "metric": data.get("metric", data.get("datapoint", "")),
            "value": data.get("value", data.get("currentValue", "")),
            "threshold": data.get("threshold", ""),
            "resource_group": data.get(
                "resourceGroup", data.get("group", "")
            ),
            "timestamp": data.get(
                "timestamp", data.get("startEpoch", "")
            ),
            "status": status.lower() if isinstance(status, str) else status,
            "raw": data,
        }
    }
