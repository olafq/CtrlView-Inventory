from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.db.models.product import Product
from app.db.models.external_item import ExternalItem
from app.modules.integrations.mercadolibre.service import (
    get_valid_ml_access_token,
)

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre API"],
)

ML_API_BASE = "https://api.mercadolibre.com"


# =========================================================
# DEBUG / VALIDACIÓN
# =========================================================
@router.get("/me")
def get_my_ml_account(
    channel_id: int = 1,
    db: Session = Depends(get_db),
):
    """
    Devuelve la cuenta MercadoLibre conectada (users/me).
    Útil para debug.
    """

    token = get_valid_ml_access_token(db, channel_id)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    r = requests.get(
        f"{ML_API_BASE}/users/me",
        headers=headers,
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


# =========================================================
# LISTAR ITEMS DEL VENDEDOR (API ML)
# =========================================================
@router.get("/items")
def list_my_items(
    channel_id: int = 1,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Lista los items del vendedor conectado desde MercadoLibre.
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

    headers = {
        "Authorization": f"Bearer {token}",
    }

    SITE_ID = "MLA"

    r = requests.get(
        f"{ML_API_BASE}/sites/{SITE_ID}/search",
        headers=headers,
        params={
            "seller_id": auth.ml_user_id,
            "limit": limit,
            "offset": offset,
        },
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    data = r.json()

    return {
        "user_id": auth.ml_user_id,
        "paging": data.get("paging"),
        "results": data.get("results"),
    }


@router.get("/items/{item_id}")
def get_item_detail(
    item_id: str,
    channel_id: int = 1,
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle completo de un item de MercadoLibre.
    """

    token = get_valid_ml_access_token(db, channel_id)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    r = requests.get(
        f"{ML_API_BASE}/items/{item_id}",
        headers=headers,
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.text,
        )

    return r.json()


# =========================================================
# 📦 PRODUCTS (DB LOCAL)
# =========================================================
@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    """
    Lista todos los products guardados en la base local.
    """

    products = db.query(Product).all()

    return [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "stock_total": p.stock_total,
            "stock_available": p.stock_available,
            "is_active": p.is_active,
            "created_at": p.created_at,
        }
        for p in products
    ]


# =========================================================
# 🔗 EXTERNAL ITEMS (DB LOCAL)
# =========================================================
@router.get("/external-items")
def list_external_items(db: Session = Depends(get_db)):

    items = (
        db.query(ExternalItem)
        .join(Product)
        .all()
    )

    return [
        {
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name,   # 👈 NUEVO
            "channel_id": i.channel_id,
            "external_item_id": i.external_item_id,
            "external_sku": i.external_sku,
            "price": float(i.price) if i.price else None,
            "stock": i.stock,
            "status": i.status,
            "created_at": i.created_at,
        }
        for i in items
    ]