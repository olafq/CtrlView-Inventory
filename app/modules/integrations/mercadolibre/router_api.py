from fastapi import APIRouter, Depends, HTTPException, Query
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
    prefix="",
    tags=["MercadoLibre API"],
)

ML_API_BASE = "https://api.mercadolibre.com"


# =========================================================
# DEBUG / VALIDACIÓN
# =========================================================
@router.get("/me")
def get_my_ml_account(
    channel_id: int,
    tenant_id: int,
    db: Session = Depends(get_db),
):
    """
    Devuelve la cuenta MercadoLibre conectada (users/me).
    Usa el MercadoLibreClient para asegurar que el token sea válido (Auto-Refresh).
    """
    from app.modules.integrations.mercadolibre.service import get_ml_client
    
    try:
        # 1. Obtenemos el cliente (maneja el refresh automáticamente)
        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        
        # 2. Llamamos al método del cliente
        user_data = client.get_current_user()
        
        return user_data

    except Exception as e:
        print(f"❌ Error en /me: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error al obtener cuenta de Mercado Libre: {str(e)}"
        )

@router.get("/items/{item_id}")
def get_item_detail(
    item_id: str,
    channel_id: int,
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle completo de un item directamente desde la API de MercadoLibre.
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
def list_products(
    tenant_id: int, 
    db: Session = Depends(get_db)
):
    """
    Lista todos los productos maestros de un tenant específico.
    """
    products = db.query(Product).filter(Product.tenant_id == tenant_id).all()

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
# LISTAR ITEMS (HÍBRIDO: DB LOCAL CON FILTROS REALES)
# =========================================================
@router.get("/items")
def list_my_items(
    tenant_id: int,
    channel_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Lista los items de la base de datos local filtrando por tenant y canal.
    """
    query = db.query(ExternalItem).filter(
        ExternalItem.tenant_id == tenant_id,
        ExternalItem.channel_id == channel_id
    )

    items = query.limit(limit).offset(offset).all()

    return [
        {
            "id": i.id,
            "external_item_id": i.external_item_id,
            "external_sku": i.external_sku,
            "external_title": i.external_title, # <--- AGREGADO: El nombre real de ML
            "price": float(i.price) if i.price else 0.0,
            "stock": i.stock,
            "status": i.status,
            "tenant_id": i.tenant_id,
            "channel_id": i.channel_id
        }
        for i in items
    ]

# ... (get_item_detail y list_products se mantienen igual)

# =========================================================
# 🔗 EXTERNAL ITEMS (VISTA DETALLADA SIN BLOQUEO DE NULLS)
# =========================================================
@router.get("/external-items")
def list_external_items(
    tenant_id: int,
    channel_id: int,
    db: Session = Depends(get_db)
):
    """
    Lista items externos permitiendo product_id NULL (outer join implícito).
    """
    items = (
        db.query(ExternalItem)
        .filter(
            ExternalItem.tenant_id == tenant_id,
            ExternalItem.channel_id == channel_id
        )
        .all()
    )

    return [
        {
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name if i.product else "SIN VINCULAR",
            "channel_id": i.channel_id,
            "external_item_id": i.external_item_id,
            "external_sku": i.external_sku,
            "external_title": i.external_title, # <--- AGREGADO: Para consistencia en ambas vistas
            "price": float(i.price) if i.price else 0.0,
            "stock": i.stock,
            "status": i.status,
            "created_at": i.created_at,
        }
        for i in items
    ]