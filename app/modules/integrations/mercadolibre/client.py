import requests
from sqlalchemy.orm import Session

from app.db.models import Channel
from app.modules.integrations.mercadolibre.service import (
    get_valid_ml_access_token,
)


class MercadoLibreClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    # =========================
    # USER
    # =========================
    def get_current_user(self) -> dict:
        url = f"{self.BASE_URL}/users/me"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    # =========================
    # ITEMS (OFICIAL SELLER)
    # =========================
    def get_item_ids(
        self,
        seller_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        url = f"{self.BASE_URL}/users/{seller_id}/items/search"
        params = {
            "limit": limit,
            "offset": offset,
        }
        r = requests.get(url, headers=self.headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_item_detail(self, item_id: str) -> dict:
        url = f"{self.BASE_URL}/items/{item_id}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()


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
# =========================
# List the Orders
# =========================

def get_orders(self, seller_id: int, offset: int = 0, limit: int = 50) -> dict:
    url = f"{self.BASE_URL}/orders/search"
    params = {
        "seller": seller_id,
        "offset": offset,
        "limit": limit,
        "sort": "date_desc",
    }
    r = requests.get(url, headers=self.headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()
