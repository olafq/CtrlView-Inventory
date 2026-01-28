import os
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.mercadolibre_auth import MercadoLibreAuth


# =========================
# ENV
# =========================
ML_CLIENT_ID = os.getenv("MERCADOLIBRE_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("MERCADOLIBRE_CLIENT_SECRET")
ML_REDIRECT_URI = os.getenv("MERCADOLIBRE_REDIRECT_URI")

AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


# =========================
# OAUTH LOGIN (YA FUNCIONA)
# =========================
def build_login_url(db: Session, channel_id: int) -> str:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise Exception("Channel not found")

    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_REDIRECT_URI,
    }

    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{AUTH_URL}?{query}"


def handle_callback(db: Session, code: str) -> MercadoLibreAuth:
    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }

    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()
    expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

    # MercadoLibre channel
    channel = db.query(Channel).filter(Channel.type == "mercadolibre").first()
    if not channel:
        raise Exception("MercadoLibre channel not found")

    auth = (
        db.query(MercadoLibreAuth)
        .filter(MercadoLibreAuth.channel_id == channel.id)
        .first()
    )

    if not auth:
        auth = MercadoLibreAuth(
            channel_id=channel.id,
            ml_user_id=data["user_id"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data.get("token_type"),
            scope=data.get("scope"),
            expires_at=expires_at,
        )
        db.add(auth)
    else:
        auth.access_token = data["access_token"]
        auth.refresh_token = data["refresh_token"]
        auth.expires_at = expires_at
        auth.ml_user_id = data["user_id"]

    db.commit()
    db.refresh(auth)
    return auth


# =========================
# TOKEN MANAGEMENT (NUEVO)
# =========================
def _is_token_expired(expires_at: datetime, buffer_minutes: int = 5) -> bool:
    """
    Devuelve True si el token está vencido o por vencer.
    """
    return datetime.utcnow() >= expires_at - timedelta(minutes=buffer_minutes)


def _refresh_access_token(db: Session, auth: MercadoLibreAuth) -> MercadoLibreAuth:
    payload = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": auth.refresh_token,
    }

    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code != 200:
        raise Exception(f"Refresh failed: {response.text}")

    data = response.json()

    auth.access_token = data["access_token"]
    auth.refresh_token = data["refresh_token"]
    auth.expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

    db.commit()
    db.refresh(auth)
    return auth


def get_valid_ml_access_token(db: Session, channel_id: int) -> str:
    """
    FUNCIÓN CLAVE DEL SISTEMA

    - Devuelve SIEMPRE un access_token válido
    - Si está vencido, lo refresca solo
    """

    auth = (
        db.query(MercadoLibreAuth)
        .filter(MercadoLibreAuth.channel_id == channel_id)
        .first()
    )

    if not auth:
        raise Exception("MercadoLibre not connected for this channel")

    if _is_token_expired(auth.expires_at):
        auth = _refresh_access_token(db, auth)

    return auth.access_token
