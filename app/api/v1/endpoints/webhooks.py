import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.integrations import (
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
)
from app.services.integration_services import WebhookService

router = APIRouter()


@router.post("", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def register_webhook(
    req: WebhookSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WebhookService(db)
    sub = await service.register_subscription(
        name=req.name,
        target_url=req.target_url,
        event_types=req.event_types,
        headers_json=req.headers_json,
    )
    return sub


@router.post("/deliveries/{delivery_id}/replay", response_model=WebhookDeliveryResponse)
async def replay_webhook_delivery(
    delivery_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WebhookService(db)
    delivery = await service.replay_delivery(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery record not found")
    return delivery
