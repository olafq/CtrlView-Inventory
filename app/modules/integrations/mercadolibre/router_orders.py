from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import requests
from datetime import datetime

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.db.models.sales import Sale
from app.db.models.channel import Channel
from app.modules.integrations.mercadolibre.service import (
    get_valid_ml_access_token,
    sync_orders,
)

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre Orders"],
)

ML_API_BASE = "https://api.mercadolibre.com"


# ==========================================================
# 🟢 LIST ORDERS (ERP SOURCE OF TRUTH - PRO)
# ==========================================================
@router.get("/orders")
def list_local_orders(
    channel_id: int = Query(...),
    status: Optional[str] = None,
    order_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Orders PRO endpoint

    Soporta:
    - status
    - order_id search
    - date range
    - pagination
    """

    query = (
        db.query(Sale, Channel)
        .join(Channel, Sale.channel_id == Channel.id)
        .filter(Sale.channel_id == channel_id)
    )

    # 🔹 Status filter
    if status:
        query = query.filter(Sale.status == status)

    # 🔹 Search by Order ID
    if order_id:
        query = query.filter(
            Sale.external_order_id.ilike(f"%{order_id}%")
        )

    # 🔹 Date filters
    if date_from:
        query = query.filter(Sale.created_at >= date_from)

    if date_to:
        query = query.filter(Sale.created_at <= date_to)

    total_count = query.count()

    results = (
        query.order_by(desc(Sale.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "meta": {
            "total": total_count,
            "offset": offset,
            "limit": limit,
        },
        "data": [
            {
                "id": sale.id,
                "external_order_id": sale.external_order_id,
                "status": sale.status,
                "total_amount": float(sale.total_amount or 0),
                "currency": sale.currency,
                "created_at": sale.created_at,
                "ml_last_updated": sale.ml_last_updated,
                "channel": channel.type,
                "channel_name": channel.name,
            }
            for sale, channel in results
        ],
    }


# ==========================================================
# 🔵 RAW ORDERS (DEBUG ONLY)
# ==========================================================
@router.get("/orders/raw")
def list_ml_orders_raw(
    channel_id: int,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Trae órdenes directamente desde Mercado Libre.
    SOLO debug.
    """

    token = get_valid_ml_access_token(db, channel_id)

    auth = (
        db.query(MercadoLibreAuth)
        .filter(MercadoLibreAuth.channel_id == channel_id)
        .first()
    )

    if not auth or not auth.ml_user_id:
        raise HTTPException(
            status_code=400,
            detail="MercadoLibre not connected for this channel",
        )

    headers = {"Authorization": f"Bearer {token}"}

    params = {
        "seller": auth.ml_user_id,
        "offset": offset,
        "limit": limit,
        "sort": "date_desc",
    }

    r = requests.get(
        f"{ML_API_BASE}/orders/search",
        headers=headers,
        params=params,
        timeout=15,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


# ==========================================================
# 🔁 MANUAL SYNC (ENTERPRISE READY)
# ==========================================================
@router.post("/orders/sync")
def sync_ml_orders(
    channel_id: int,
    db: Session = Depends(get_db),
):
    """
    Sincronización manual.
    En arquitectura profesional,
    esto es fallback, no mecanismo principal.
    """

    result = sync_orders(db, channel_id=channel_id)

    return {
        "message": "Manual sync completed",
        "processed_orders": result.get("processed_orders", 0),
        "timestamp": datetime.utcnow(),
    }
