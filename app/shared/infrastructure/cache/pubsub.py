from google.cloud.pubsub_v1 import PublisherClient

from app.config import settings

"""
Create a Google Cloud Pub/Sub publisher client instance using the project ID from the
settings. This client will be used to publish messages to the specified Pub/Sub topic
for event-driven communication between services. The publisher client will be initialized
lazily on first use, avoiding credential lookup at import time.
"""  # noqa: E501


def get_pubsub_client() -> PublisherClient:
    """Lazily initialize and return the Pub/Sub publisher client."""
    if not hasattr(get_pubsub_client, "_client"):
        get_pubsub_client._client = PublisherClient()
    return get_pubsub_client._client


def get_topic_path() -> str:
    """Lazily compute and return the fully qualified Pub/Sub topic path."""
    return get_pubsub_client().topic_path(
        settings.gcp_project_id, settings.pubsub_topic_id
    )
