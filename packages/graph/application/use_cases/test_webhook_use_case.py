"""Backward compatibility aliases for webhook testing use case."""

from application.ports.base import WebhookServicePort as WebhookDeliveryPort

from .dto import TestWebhookRequestDTO as TestWebhookRequest
from .dto import WebhookTestResultDTO as TestWebhookResponse
from .webhook.test_webhook_use_case import TestWebhookUseCase

__all__ = [
    "WebhookDeliveryPort",
    "TestWebhookRequest",
    "TestWebhookResponse",
    "TestWebhookUseCase",
]
