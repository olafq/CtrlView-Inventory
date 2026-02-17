from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.db.models.sales import Sale
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
# 🟢 LIST ORDERS DESDE TU BASE (ERP SOURCE OF TRUTH)
# ==========================================================
@router.get("/orders")
def list_local_orders(
    channel_id: int = 1,
    db: Session = Depends(get_db),
):
    """
    Devuelve órdenes almacenadas en tu sistema (tabla sales).
    Esta es la fuente real para la UI.
    """

    sales = (
        db.query(Sale)
        .filter(Sale.channel_id == channel_id)
        .order_by(Sale.id.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "external_order_id": s.external_order_id,
            "status": s.status,
            "total_amount": float(s.total_amount or 0),
            "currency": s.currency,
            "created_at": s.created_at,
            "ml_last_updated": s.ml_last_updated,

            # 👇 NUEVO
            "channel": s.channel.type if s.channel else None,
            "channel_name": s.channel.name if s.channel else None,
        }
        for s in sales
    ]


# ==========================================================
# 🔵 RAW ORDERS DIRECTO DESDE MERCADO LIBRE (DEBUG)
# ==========================================================
@router.get("/orders/raw")
def list_ml_orders_raw(
    channel_id: int = 1,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Trae órdenes directamente desde ML.
    Solo para debug / comparación.
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

    seller_id = auth.ml_user_id

    headers = {
        "Authorization": f"Bearer {token}",
    }

    params = {
        "seller": seller_id,
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

    data = r.json()

    return {
        "seller_id": seller_id,
        "paging": data.get("paging"),
        "results": data.get("results"),
    }


# ==========================================================
# 🔁 SYNC ORDERS (ML → TU BASE)
# ==========================================================
@router.post("/orders/sync")
def sync_ml_orders(
    channel_id: int = 1,
    db: Session = Depends(get_db),
):
    """
    Sincroniza órdenes de ML a tu base.
    Aplica lógica de stock automática.
    """

    result = sync_orders(db, channel_id=channel_id)
    return result

