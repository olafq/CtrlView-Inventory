from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import Channel, CatalogImportRun
from app.modules.integrations.mercadolibre.tasks import import_mercadolibre_task
from fastapi.responses import RedirectResponse

import os
import requests

router = APIRouter(
    prefix="/integrations/mercadolibre/imports",
    tags=["MercadoLibre"]
)

@router.post("/imports/start")
def start_import(db: Session = Depends(get_db)):
    channel = (
        db.query(Channel)
        .filter(Channel.type == "mercadolibre")
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="MercadoLibre channel not found")

    run = CatalogImportRun(
        channel_id=channel.id,
        status="queued",
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    import_mercadolibre_task.delay(run.id)

    return {
        "id": run.id,
        "channel_id": run.channel_id,
        "status": run.status,
        "started_at": run.started_at,
    }


router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre"]
)

ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
REDIRECT_URI = os.getenv(
    "ML_REDIRECT_URI",
    "https://oauth.goqconsultant.com/integrations/mercadolibre/oauth/callback"
)

@router.get("/oauth/start")
def oauth_start():
    url = (
        "https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={ML_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return RedirectResponse(url)



ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")

@router.get("/oauth/callback")
def oauth_callback(code: str):
    token_url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(token_url, data=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=response.text
        )

    data = response.json()

    # 🔐 POR AHORA solo devolvemos el token (después lo guardamos en DB)
    return {
        "access_token": data["access_token"],
        "user_id": data["user_id"],
        "expires_in": data["expires_in"],
    }

