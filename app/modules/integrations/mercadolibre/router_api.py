from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
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
# LISTAR ITEMS DEL VENDEDOR
# =========================================================
@router.get("/items")
def list_my_items(
    channel_id: int = 1,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Lista los items del vendedor conectado.
    Usa:
    - access_token válido
    - ml_user_id guardado en DB
    - Authorization Bearer (forma correcta)
    """

    # 1️⃣ Token válido (con refresh automático)
    token = get_valid_ml_access_token(db, channel_id)

    # 2️⃣ Obtener auth desde DB (ml_user_id YA GUARDADO)
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

    user_id = auth.ml_user_id

    # 3️⃣ Llamada correcta según documentación oficial
    headers = {
        "Authorization": f"Bearer {token}",
    }

    SITE_ID = "MLA"  # Argentina

    r = requests.get(
        f"{ML_API_BASE}/sites/{SITE_ID}/search",
        headers=headers,
        params={
            "seller_id": user_id,
            "limit": limit,
            "offset": offset,
        },
        timeout=10,
    )


    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    data = r.json()

    return {
        "user_id": user_id,
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
    Endpoint permitido incluso con apps nuevas.
    """

    # 1️⃣ Token válido (refresh automático)
    token = get_valid_ml_access_token(db, channel_id)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    # 2️⃣ Llamada directa al item
    r = requests.get(
        f"https://api.mercadolibre.com/items/{item_id}",
        headers=headers,
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.text,
        )

    return r.json()
