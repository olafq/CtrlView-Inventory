import os
import json
import base64
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
# HELPERS
# =========================
def _encode_state(payload: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_state(state: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(state.encode()).decode())


# =========================
# OAUTH FLOW
# =========================
def build_login_url(db: Session, channel_id: int) -> str:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise Exception("Channel not found")

    state = _encode_state({
        "v": "v1",
        "channel_id": channel_id
    })

    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_REDIRECT_URI,
        "state": state,
    }

    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{AUTH_URL}?{query}"


def handle_callback(db: Session, code: str, state: str) -> MercadoLibreAuth:
    decoded = _decode_state(state)
    channel_id = decoded.get("channel_id")

    if not channel_id:
        raise Exception("Invalid state")

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise Exception("Channel not found")

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

    auth = db.query(MercadoLibreAuth).filter(
        MercadoLibreAuth.channel_id == channel.id
    ).first()

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
# TOKEN MANAGEMENT
# =========================
def refresh_access_token(db: Session, auth: MercadoLibreAuth) -> MercadoLibreAuth:
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


def get_valid_access_token(db: Session, channel_id: int) -> str:
    auth = db.query(MercadoLibreAuth).filter(
        MercadoLibreAuth.channel_id == channel_id
    ).first()

    if not auth:
        raise Exception("MercadoLibre not connected")

    # si vence en menos de 2 min → refresh
    if auth.expires_at <= datetime.utcnow() + timedelta(minutes=2):
        auth = refresh_access_token(db, auth)

    return auth.access_token
    