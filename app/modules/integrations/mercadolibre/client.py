import requests
from sqlalchemy.orm import Session

from app.db.models import Channel



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
    # ORDERS
    # =========================
    def get_orders(
        self,
        seller_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        url = f"{self.BASE_URL}/orders/search"
        params = {
            "seller": seller_id,
            "limit": limit,
            "offset": offset,
            "sort": "date_desc",
        }

        r = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

