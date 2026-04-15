from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime

from app.db.dependencies import get_db
from app.db.models.sales import Sale
from app.db.models.channel import Channel
from app.core.tenant import get_current_tenant
from app.db.models import Tenant
from app.modules.integrations.mercadolibre.service import sync_orders

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre Orders"],
)

@router.get("/orders")
def list_local_orders(
    status: Optional[str] = None,
    order_id: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    # Pro Tip: Usamos Join para traer el canal y validar que pertenezca al tenant
    query = db.query(Sale, Channel).join(
        Channel, Sale.channel_id == Channel.id
    ).filter(
        Sale.tenant_id == tenant.id
    )

    if status:
        query = query.filter(Sale.status == status)
    if order_id:
        query = query.filter(Sale.external_order_id.ilike(f"%{order_id}%"))

    total_count = query.count()
    results = query.order_by(desc(Sale.created_at)).offset(offset).limit(limit).all()

    return {
        "meta": {"total": total_count, "offset": offset, "limit": limit},
        "data": [
            {
                "id": sale.id,
                "external_order_id": sale.external_order_id,
                "status": sale.status,
                "total_amount": float(sale.total_amount or 0),
                "currency": sale.currency,
                "created_at": sale.created_at,
                "channel_name": channel.name,
                "channel_type": channel.channel_type
            }
            for sale, channel in results
        ],
    }