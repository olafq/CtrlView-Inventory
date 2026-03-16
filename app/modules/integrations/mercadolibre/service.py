import os
import requests
import  json
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.db.models.product import Product
from app.db.models.stock_movement import StockMovement
from app.db.models.sales import Sale
from app.db.models.external_item import ExternalItem
from app.modules.integrations.mercadolibre.client import MercadoLibreClient


# =========================
# ENV
# =========================
ML_CLIENT_ID = os.getenv("MERCADOLIBRE_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("MERCADOLIBRE_CLIENT_SECRET")
ML_REDIRECT_URI = os.getenv("MERCADOLIBRE_REDIRECT_URI")

AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

DEFAULT_SYNC_LIMIT = int(os.getenv("ML_SYNC_LIMIT", "50"))


# =========================
# HELPERS
# =========================
def _require_env() -> None:
    if not ML_CLIENT_ID or not ML_CLIENT_SECRET or not ML_REDIRECT_URI:
        raise Exception("Missing MercadoLibre OAuth env vars (CLIENT_ID / CLIENT_SECRET / REDIRECT_URI)")


def _is_token_expired(expires_at: datetime, buffer_minutes: int = 5) -> bool:
    return datetime.utcnow() >= expires_at - timedelta(minutes=buffer_minutes)


# =========================
# OAUTH LOGIN (tenant-safe)
# =========================
def build_login_url(db: Session, channel_id: int, tenant_id: int) -> str:
    """
    Devuelve URL de login para MercadoLibre.
    Usa state para transportar tenant_id + channel_id en el callback.
    """
    _require_env()

    channel = (
        db.query(Channel)
        .filter(
            Channel.id == channel_id,
            Channel.tenant_id == tenant_id,
        )
        .first()
    )
    if not channel:
        raise Exception("Channel not found for this tenant")

    state_payload = {
        "tenant_id": tenant_id,
        "channel_id": channel_id,
    }

    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_REDIRECT_URI,
        "state": json.dumps(state_payload),
    }

    query = urllib.parse.urlencode(params)
    return f"{AUTH_URL}?{query}"

def parse_oauth_state(state: str) -> Dict[str, int]:
    try:
        data = json.loads(state)

        tenant_id = int(data["tenant_id"])
        channel_id = int(data["channel_id"])

        return {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
        }
    except Exception:
        raise Exception("Invalid OAuth state")
def handle_callback(db: Session, code: str, channel_id: int, tenant_id: int) -> MercadoLibreAuth:
    """
    Intercambia code por tokens y guarda auth POR TENANT.
    """
    _require_env()

    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }

    response = requests.post(TOKEN_URL, data=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()
    expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))

    # ✅ Auth por tenant + channel
    auth = (
        db.query(MercadoLibreAuth)
        .filter(
            MercadoLibreAuth.channel_id == channel_id,
            MercadoLibreAuth.tenant_id == tenant_id,
        )
        .first()
    )

    if not auth:
        auth = MercadoLibreAuth(
            tenant_id=tenant_id,
            channel_id=channel_id,
            ml_user_id=str(data.get("user_id")) if data.get("user_id") is not None else None,
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
        if data.get("user_id") is not None:
            auth.ml_user_id = str(data["user_id"])
        auth.token_type = data.get("token_type")
        auth.scope = data.get("scope")

    db.commit()
    db.refresh(auth)
    return auth


# =========================
# TOKEN MANAGEMENT (tenant-safe)
# =========================
def _refresh_access_token(db: Session, auth: MercadoLibreAuth) -> MercadoLibreAuth:
    _require_env()

    payload = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": auth.refresh_token,
    }

    response = requests.post(TOKEN_URL, data=payload, timeout=20)
    if response.status_code != 200:
        raise Exception(f"Refresh failed: {response.text}")

    data = response.json()

    auth.access_token = data["access_token"]
    auth.refresh_token = data["refresh_token"]
    auth.expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))

    # opcional
    if data.get("user_id") is not None:
        auth.ml_user_id = str(data["user_id"])

    db.commit()
    db.refresh(auth)
    return auth


def get_valid_ml_access_token(db: Session, channel_id: int, tenant_id: int) -> str:
    """
    Devuelve SIEMPRE un access_token válido por tenant.
    """
    auth = (
        db.query(MercadoLibreAuth)
        .filter(
            MercadoLibreAuth.channel_id == channel_id,
            MercadoLibreAuth.tenant_id == tenant_id,
        )
        .first()
    )

    if not auth:
        raise Exception("MercadoLibre not connected for this tenant/channel")

    if not auth.expires_at:
        raise Exception("MercadoLibre auth missing expires_at")

    if _is_token_expired(auth.expires_at):
        auth = _refresh_access_token(db, auth)

    return auth.access_token


# =========================
# MOCK ORDERS (debug)
# =========================
def get_mock_orders_scenario() -> Dict[str, Any]:
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
                        {"item": {"id": "MLA1967804304"}, "quantity": 2}
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
                        {"item": {"id": "MLA1967804304"}, "quantity": 2}
                    ],
                }
            ]
        }

    return {"results": []}


# =========================
# STOCK RECALC (enterprise)
# =========================
def recalculate_product_stock(db: Session, product: Product) -> None:
    """
    Enterprise-ready:
    - NO commit acá (se commitea al final del sync)
    """
    movements = (
        db.query(StockMovement)
        .filter(StockMovement.product_id == product.id)
        .all()
    )
    product.stock_total = sum(m.quantity for m in movements)


# =========================
# ML CLIENT (tenant-safe)
# =========================
def get_ml_client(db: Session, channel_id: int, tenant_id: int) -> MercadoLibreClient:
    access_token = get_valid_ml_access_token(db, channel_id=channel_id, tenant_id=tenant_id)
    return MercadoLibreClient(access_token)


# =========================
# SYNC ORDERS (tenant-safe)
# =========================
def sync_orders(
    db: Session,
    channel_id: int,
    tenant_id: int,
    limit: int = DEFAULT_SYNC_LIMIT,
) -> Dict[str, Any]:
    """
    - 100% tenant safe (no cruza data)
    - idempotente movimientos
    - paid/cancel/refund/partial_refund
    """

    debug_mode = os.getenv("ML_DEBUG_MODE", "false").lower() == "true"

    processed = 0
    created = 0
    updated = 0
    skipped_unchanged = 0
    missing_mapping = 0
    movements_created = 0
    movements_refunded = 0

    try:
        if debug_mode:
            data = get_mock_orders_scenario()
        else:
            # auth por tenant
            auth = (
                db.query(MercadoLibreAuth)
                .filter(
                    MercadoLibreAuth.channel_id == channel_id,
                    MercadoLibreAuth.tenant_id == tenant_id,
                )
                .first()
            )
            if not auth or not auth.ml_user_id:
                raise Exception("MercadoLibre not connected (missing ml_user_id) for this tenant/channel")

            client = get_ml_client(db, channel_id, tenant_id)
            data = client.get_orders(seller_id=auth.ml_user_id, limit=limit)

        results = data.get("results", [])

        for order in results:
            external_order_id = str(order.get("id"))
            new_status = order.get("status")
            last_updated = order.get("date_last_updated")

            if not external_order_id:
                continue

            existing = (
                db.query(Sale)
                .filter(
                    Sale.external_order_id == external_order_id,
                    Sale.tenant_id == tenant_id,
                    Sale.channel_id == channel_id,
                )
                .first()
            )

            # NUEVA ORDEN
            if not existing:
                sale = Sale(
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    external_order_id=external_order_id,
                    total_amount=order.get("total_amount"),
                    currency=order.get("currency_id"),
                    status=new_status,
                    ml_last_updated=last_updated,
                )
                db.add(sale)
                db.flush()

                created += 1

                if new_status == "paid":
                    res = create_stock_movements(db, sale, order)
                    movements_created += res["movements_created"]
                    missing_mapping += res["missing_mapping"]

            # ORDEN EXISTENTE
            else:
                if existing.ml_last_updated == last_updated:
                    skipped_unchanged += 1
                    continue

                old_status = existing.status

                existing.status = new_status
                existing.ml_last_updated = last_updated
                existing.total_amount = order.get("total_amount")
                existing.currency = order.get("currency_id")

                updated += 1

                if old_status != "paid" and new_status == "paid":
                    res = create_stock_movements(db, existing, order)
                    movements_created += res["movements_created"]
                    missing_mapping += res["missing_mapping"]

                elif old_status == "paid" and new_status in ["cancelled", "refunded", "partially_refunded"]:
                    res = revert_stock_movements(db, existing)
                    movements_refunded += res["movements_refunded"]

            processed += 1

        db.commit()

        return {
            "processed_orders": processed,
            "created_orders": created,
            "updated_orders": updated,
            "skipped_unchanged": skipped_unchanged,
            "missing_item_mappings": missing_mapping,
            "movements_created": movements_created,
            "movements_refunded": movements_refunded,
        }

    except Exception:
        db.rollback()
        raise


# =========================
# MOVEMENTS (tenant-safe)
# =========================
def create_stock_movements(db: Session, sale: Sale, order: Dict[str, Any]) -> Dict[str, int]:
    existing_movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.sale_id == sale.id,
            StockMovement.reason == "sale",
        )
        .count()
    )

    if existing_movements > 0:
        return {"movements_created": 0, "missing_mapping": 0}

    movements_created = 0
    missing_mapping = 0

    for item in order.get("order_items", []):
        item_id = item.get("item", {}).get("id")
        quantity = item.get("quantity", 0)

        if not item_id or not quantity:
            continue

        external_item = (
            db.query(ExternalItem)
            .filter(
                ExternalItem.external_item_id == item_id,
                ExternalItem.channel_id == sale.channel_id,
                ExternalItem.tenant_id == sale.tenant_id,
            )
            .first()
        )

        if not external_item:
            missing_mapping += 1
            continue

        movement = StockMovement(
            product_id=external_item.product_id,
            sale_id=sale.id,
            quantity=-abs(int(quantity)),
            reason="sale",
        )
        db.add(movement)
        movements_created += 1

        recalculate_product_stock(db, external_item.product)

    return {"movements_created": movements_created, "missing_mapping": missing_mapping}


def revert_stock_movements(db: Session, sale: Sale) -> Dict[str, int]:
    existing_refunds = (
        db.query(StockMovement)
        .filter(
            StockMovement.sale_id == sale.id,
            StockMovement.reason == "refund",
        )
        .count()
    )

    if existing_refunds > 0:
        return {"movements_refunded": 0}

    sale_movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.sale_id == sale.id,
            StockMovement.reason == "sale",
        )
        .all()
    )

    movements_refunded = 0

    for m in sale_movements:
        product = m.product

        revert = StockMovement(
            product_id=product.id,
            sale_id=sale.id,
            quantity=abs(int(m.quantity)),
            reason="refund",
        )
        db.add(revert)
        movements_refunded += 1

        recalculate_product_stock(db, product)

    return {"movements_refunded": movements_refunded}