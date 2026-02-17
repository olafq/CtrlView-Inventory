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
# ORDERS GENERADAS (PRUEBAS)
# ========================= 

def get_mock_orders_scenario():
    """
    Simula distintos escenarios de órdenes.
    Cambiá el Escenario manualmente para probar casos.
    """

    scenario = os.getenv("ML_DEBUG_SCENARIO", "paid")

    if scenario == "paid":
        return {
            "results": [
                {
                    "id": "TEST_ORDER_1",
                    "status": "paid",
                    "total_amount": 1000,
                    "currency_id": "ARS",
                    "date_last_updated": "2025-01-01T00:00:00Z",
                    "order_items": [
                        {
                            "item": {"id": "MLA1967804304"},
                            "quantity": 2,
                        }
                    ],
                }
            ]
        }

    if scenario == "cancelled":
        return {
            "results": [
                {
                    "id": "TEST_ORDER_1",
                    "status": "cancelled",
                    "total_amount": 1000,
                    "currency_id": "ARS",
                    "date_last_updated": "2025-01-02T00:00:00Z",
                    "order_items": [
                        {
                            "item": {"id": "MLA1967804304"},
                            "quantity": 2,
                        }
                    ],
                }
            ]
        }

    return {"results": []}

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
    debug_mode = os.getenv("ML_DEBUG_MODE", "false").lower() == "true"

    if debug_mode:
        print("⚠ DEBUG MODE ENABLED")
        data = get_mock_orders_scenario()
    else:
        data = client.get_orders(seller_id=seller_id, limit=limit)

    results = data.get("results", [])
    processed = 0

    for order in results:

        external_order_id = str(order["id"])
        new_status = order.get("status")
        last_updated = order.get("date_last_updated")

        existing = (
            db.query(Sale)
            .filter(Sale.external_order_id == external_order_id)
            .first()
        )

        # =========================
        # NUEVA ORDEN
        # =========================
        if not existing:

            sale = Sale(
                channel_id=channel_id,
                external_order_id=external_order_id,
                total_amount=order.get("total_amount"),
                currency=order.get("currency_id"),
                status=new_status,
                ml_last_updated=last_updated,
            )

            db.add(sale)
            db.flush()

            if new_status == "paid":
                create_stock_movements(db, sale, order)

        # =========================
        # ORDEN EXISTENTE
        # =========================
        else:

            # 🔒 Si no cambió nada → no hacemos nada
            if existing.ml_last_updated == last_updated:
                continue

            old_status = existing.status

            existing.status = new_status
            existing.ml_last_updated = last_updated

            # 🟢 Caso 1: pasa a paid
            if old_status != "paid" and new_status == "paid":
                create_stock_movements(db, existing, order)

            # 🔴 Caso 2: pasa de paid a cancelado o refund
            elif old_status == "paid" and new_status in ["cancelled", "refunded"]:
                revert_stock_movements(db, existing)

            # 🟡 Caso 3: partial refund
            elif old_status == "paid" and new_status == "partially_refunded":
                revert_stock_movements(db, existing)

        processed += 1

    db.commit()

    return {
        "processed_orders": processed
    }

# =========================
# FACTORY
# =========================
def get_ml_client(db: Session, channel_id: int) -> MercadoLibreClient:
    access_token = get_valid_ml_access_token(db, channel_id)
    return MercadoLibreClient(access_token)
# =========================
# FUNCIONES AUXILIARES
# =========================
def create_stock_movements(db: Session, sale: Sale, order: dict):

    existing_movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.sale_id == sale.id,
            StockMovement.reason == "sale",
        )
        .count()
    )

    # 🔒 Ya existen movimientos → no duplicar
    if existing_movements > 0:
        return

    for item in order.get("order_items", []):

        item_id = item["item"]["id"]
        quantity = item["quantity"]

        external_item = (
            db.query(ExternalItem)
            .filter(
                ExternalItem.external_item_id == item_id,
                ExternalItem.channel_id == sale.channel_id,
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



def revert_stock_movements(db: Session, sale: Sale):

    existing_refunds = (
        db.query(StockMovement)
        .filter(
            StockMovement.sale_id == sale.id,
            StockMovement.reason == "refund",
        )
        .count()
    )

    # 🔒 Si ya revertimos antes, no volver a revertir
    if existing_refunds > 0:
        return

    sale_movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.sale_id == sale.id,
            StockMovement.reason == "sale",
        )
        .all()
    )

    for m in sale_movements:

        product = m.product

        revert = StockMovement(
            product_id=product.id,
            sale_id=sale.id,
            quantity=abs(m.quantity),
            reason="refund",
        )

        db.add(revert)
        recalculate_product_stock(db, product)
