"""Receive Edwin AI alert events via webhook.

Edwin AI pushes alert notifications to this endpoint. Configure a
webhook integration in your LogicMonitor/Edwin AI portal pointing to
the EDA controller's webhook URL.

Arguments:
    host: Bind address for the webhook listener (default: 0.0.0.0)
    port: Port to listen on (default: 5000)
    token: Optional shared secret for HMAC signature verification
"""

import asyncio
import json
import hashlib
import hmac
import logging
from typing import Any
from aiohttp import web

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Receive Edwin AI webhook events and forward to the EDA rulebook."""
    host = str(args.get("host", "0.0.0.0"))
    port = int(args.get("port", 5000))
    token = args.get("token", "")

    app = web.Application()

    async def _handle_event(request: web.Request) -> web.Response:
        try:
            payload = await request.read()

            if token:
                signature = request.headers.get("X-Edwin-Signature", "")
                expected = hmac.new(
                    token.encode(), payload, hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(signature, expected):
                    logger.warning("Invalid webhook signature")
                    return web.Response(status=401, text="Invalid signature")

            data = json.loads(payload)
            event = _normalize_event(data)
            await queue.put(event)
            return web.Response(status=200, text="OK")
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload")
            return web.Response(status=400, text="Invalid JSON")
        except Exception as exc:
            logger.exception("Error processing webhook: %s", exc)
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


def _normalize_event(data: dict) -> dict:
    """Normalize Edwin AI webhook payload to a consistent event schema."""
    return {
        "edwin_ai": {
            "event_type": data.get("type", data.get("eventType", "alert")),
            "alert_id": data.get("alertId", data.get("id", "")),
            "severity": data.get("severity", data.get("level", "unknown")),
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
            "status": data.get(
                "status", data.get("alertStatus", "active")
            ),
            "raw": data,
        }
    }
