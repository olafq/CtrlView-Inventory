from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.modules.integrations.mercadolibre.service import get_valid_ml_access_token

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre Orders"],
)

ML_API_BASE = "https://api.mercadolibre.com"


@router.get("/orders")
def list_orders(
    channel_id: int = 1,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Lista órdenes del vendedor.
    Fuente de verdad para inventario.
    """

    # 1️⃣ Token válido
    token = get_valid_ml_access_token(db, channel_id)

    # 2️⃣ Obtener seller_id desde DB
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

    # 3️⃣ Llamada a Orders (endpoint PERMITIDO)
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
