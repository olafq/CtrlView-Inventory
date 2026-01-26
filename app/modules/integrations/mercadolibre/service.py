import base64
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models import Channel, MercadoLibreAuth
from app.modules.integrations.mercadolibre.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    refresh_access_token,
    MLOAuthError,
)

STATE_SECRET = "v1"  # simple, sin crypto (mejorable). Para empezar OK.

def _encode_state(data: dict) -> str:
    raw = json.dumps({"v": STATE_SECRET, **data}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")

def _decode_state(state: str) -> dict:
    raw = base64.urlsafe_b64decode(state.encode("utf-8"))
    data = json.loads(raw.decode("utf-8"))
    if data.get("v") != STATE_SECRET:
        raise ValueError("Invalid state")
    return data

def build_login_url(db: Session, channel_id: int) -> str:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise ValueError("Channel not found")
    if channel.type != "mercadolibre":
        raise ValueError("Channel is not MercadoLibre")

    state = _encode_state({"channel_id": channel_id})
    return get_authorization_url(state=state)

def handle_callback(db: Session, code: str, state: str) -> MercadoLibreAuth:
    try:
        payload_state = _decode_state(state)
        channel_id = int(payload_state["channel_id"])
    except Exception:
        raise ValueError("Invalid state")

    token_data = exchange_code_for_token(code)

    # token_data esperado:
    # access_token, refresh_token, expires_in, user_id, scope, token_type
    expires_at = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))

    record = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()
    if not record:
        record = MercadoLibreAuth(
            channel_id=channel_id,
            ml_user_id=int(token_data["user_id"]),
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data.get("token_type", "bearer"),
            scope=token_data.get("scope"),
            expires_at=expires_at,
        )
        db.add(record)
    else:
        record.ml_user_id = int(token_data["user_id"])
        record.access_token = token_data["access_token"]
        record.refresh_token = token_data["refresh_token"]
        record.token_type = token_data.get("token_type", "bearer")
        record.scope = token_data.get("scope")
        record.expires_at = expires_at

    db.commit()
    db.refresh(record)
    return record

def get_valid_access_token(db: Session, channel_id: int) -> str:
    record = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()
    if not record:
        raise ValueError("MercadoLibre not connected for this channel")

    # si faltan 2 minutos para expirar, refrescamos
    if record.expires_at <= datetime.utcnow() + timedelta(minutes=2):
        td = refresh_access_token(record.refresh_token)
        record.access_token = td["access_token"]
        record.refresh_token = td["refresh_token"]
        record.expires_at = datetime.utcnow() + timedelta(seconds=int(td["expires_in"]))
        record.scope = td.get("scope", record.scope)
        record.token_type = td.get("token_type", record.token_type)
        db.commit()

    return record.access_token
