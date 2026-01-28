from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.db.dependencies import get_db
from app.modules.integrations.mercadolibre.service import get_valid_ml_access_token

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre API"],
)


@router.get("/me")
def get_my_ml_account(
    channel_id: int = 1,
    db: Session = Depends(get_db),
):
    """
    Endpoint de prueba.
    Devuelve la cuenta MercadoLibre conectada.
    """

    try:
        token = get_valid_ml_access_token(db, channel_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r = requests.get(
        "https://api.mercadolibre.com/users/me",
        headers=headers,
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.text,
        )

    return r.json()


@router.get("/items")
def list_my_items(
    channel_id: int = 1,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Lista los items del vendedor conectado.
    """

    # 1️⃣ Token válido
    try:
        token = get_valid_ml_access_token(db, channel_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2️⃣ Obtener user_id
    me = requests.get(
        "https://api.mercadolibre.com/users/me",
        params={"access_token": token},
        timeout=10,
    )

    if me.status_code != 200:
        raise HTTPException(status_code=me.status_code, detail=me.text)

    user_id = me.json()["id"]

    # 3️⃣ Buscar items (⚠️ token por query param)
    r = requests.get(
        f"https://api.mercadolibre.com/users/{user_id}/items/search",
        params={
            "access_token": token,
            "limit": limit,
            "offset": offset,
        },
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return {
        "user_id": user_id,
        "paging": r.json().get("paging"),
        "results": r.json().get("results"),
    }
