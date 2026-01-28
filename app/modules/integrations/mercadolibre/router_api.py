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
