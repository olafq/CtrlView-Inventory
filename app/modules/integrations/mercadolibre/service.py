import os
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.db.models.product import Product
from app.db.models.stock_movement import StockMovement
from app.db.models.sales import Sale
from app.db.models.external_item import ExternalItem  # si existe
from app.modules.integrations.mercadolibre.client import get_ml_client
from app.modules.integrations.mercadolibre.client import MercadoLibreClient
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


# =========================
# RECALCULO DE STOCK 
# =========================
def recalculate_product_stock(
    db: Session,
    product: Product,
) -> None:
    """
    Recalcula el stock total del producto en base
    a todos los movimientos de stock.
    """

    movements = (
        db.query(StockMovement)
        .filter(StockMovement.product_id == product.id)
        .all()
    )

    # 👇 ventas = negativo, ajustes = positivo
    product.stock_total = sum(m.quantity for m in movements)

    db.commit()

# =========================
# LISTADO DE STOCK 
# =========================

def sync_orders(db: Session, channel_id: int, limit: int = 50):
    client = get_ml_client(db, channel_id)

    auth = (
        db.query(MercadoLibreAuth)
        .filter(MercadoLibreAuth.channel_id == channel_id)
        .first()
    )

    seller_id = auth.ml_user_id

    data = client.get_orders(seller_id=seller_id, limit=limit)

    results = data.get("results", [])
    created_sales = 0

    for order in results:
        if order["status"] != "paid":
            continue

        external_order_id = str(order["id"])

        existing = (
            db.query(Sale)
            .filter(Sale.external_order_id == external_order_id)
            .first()
        )

        if existing:
            continue

        sale = Sale(
            channel_id=channel_id,
            external_order_id=external_order_id,
            total_amount=order.get("total_amount"),
            currency=order.get("currency_id"),
        )

        db.add(sale)
        db.flush()

        for item in order.get("order_items", []):
            item_id = item["item"]["id"]
            quantity = item["quantity"]

            external_item = (
                db.query(ExternalItem)
                .filter(
                    ExternalItem.external_item_id == item_id,
                    ExternalItem.channel_id == channel_id,
                )
                .first()
            )

            if not external_item:
                continue

            movement = StockMovement(
                product_id=external_item.product_id,
                sale_id=sale.id,
                quantity=-abs(quantity),
                reason="sale",
            )

            db.add(movement)

            recalculate_product_stock(db, external_item.product)

        created_sales += 1

    db.commit()

    return {
        "imported_orders": created_sales
    }
# =========================
# FACTORY
# =========================
def get_ml_client(db: Session, channel_id: int) -> MercadoLibreClient:
    channel = (
        db.query(Channel)
        .filter(Channel.id == channel_id)
        .first()
    )

    if not channel or channel.type != "mercadolibre":
        raise Exception("Invalid MercadoLibre channel")

    access_token = get_valid_ml_access_token(db, channel.id)
    return MercadoLibreClient(access_token)