from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from app.modules.integrations.mercadolibre.oauth import (
    get_authorization_url,
    exchange_code_for_token,
)

router = APIRouter(prefix="/integrations/mercadolibre/oauth", tags=["MercadoLibre OAuth"])


@router.get("/login")
def login():
    url = get_authorization_url()
    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str | None = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    token_data = exchange_code_for_token(code)
    return token_data
