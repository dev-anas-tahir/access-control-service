from google.cloud.pubsub_v1 import PublisherClient

from app.config import settings

"""
Create a Google Cloud Pub/Sub publisher client instance using the project ID from the 
settings.This client will be used to publish messages to the specified Pub/Sub topic for
event-driven communication between services. The publisher client will be initialized
when the application starts and can be used throughout the application lifecycle
"""
pubsub_client: PublisherClient = PublisherClient()

"""
Build the fully qualified topic path using the project ID and topic ID from settings.
This path is required when publishing messages to the Pub/Sub topic, ensuring that
the messages are sent to the correct topic within the specified GCP project.
"""
topic_path: str = pubsub_client.topic_path(
    settings.gcp_project_id, settings.pubsub_topic_id
)
