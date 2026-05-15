"""Pub/Sub publisher for cross-service domain events."""

import json
import logging

from google.cloud.pubsub_v1 import PublisherClient

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> PublisherClient:
    if not hasattr(_get_client, "_client"):
        _get_client._client = PublisherClient()
    return _get_client._client


def _topic_path() -> str:
    return _get_client().topic_path(settings.gcp_project_id, settings.pubsub_topic_id)


async def publish_event(event_type: str, payload: dict) -> None:
    data = json.dumps(
        {"event_type": event_type, "service": "catalog-service", **payload}
    )
    try:
        _get_client().publish(_topic_path(), data.encode("utf-8"))
    except Exception:
        logger.exception("Failed to publish event %s", event_type)
