import requests
from sqlalchemy.orm import Session

from app.db.models import Channel
from app.modules.integrations.mercadolibre.service import (
    get_valid_ml_access_token,
)


class MercadoLibreClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    # =========================
    # USER
    # =========================
    def get_current_user(self) -> dict:
        """
        Devuelve info del usuario autenticado
        """
        url = f"{self.BASE_URL}/users/me"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()

    # =========================
    # ITEMS
    # =========================
    def get_item_ids(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        Devuelve IDs de publicaciones del vendedor
        """
        url = f"{self.BASE_URL}/users/{user_id}/items/search"
        params = {
            "limit": limit,
            "offset": offset,
        }
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_item_detail(self, item_id: str) -> dict:
        """
        Devuelve el detalle completo de una publicación
        """
        url = f"{self.BASE_URL}/items/{item_id}"
        response = requests.get(
            url,
            headers=self.headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()


# =========================================================
# FACTORY OFICIAL (ESTO ES LO QUE FALTABA)
# =========================================================
def get_ml_client(db: Session, channel_id: int) -> MercadoLibreClient:
    """
    Devuelve un cliente MercadoLibre listo para usar,
    con token válido (refresca solo si hace falta).
    """

    channel = (
        db.query(Channel)
        .filter(Channel.id == channel_id)
        .first()
    )

    if not channel or channel.type != "mercadolibre":
        raise Exception("Invalid MercadoLibre channel")

    access_token = get_valid_ml_access_token(db, channel.id)

    return MercadoLibreClient(access_token)
# =========================================================
# Buscar puclicaciones de MLA
# =========================================================
def search_items_by_seller(
    self,
    site_id: str,
    seller_id: int,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Busca publicaciones del vendedor usando
    /sites/{SITE_ID}/search?seller_id=
    """
    url = f"{self.BASE_URL}/sites/{site_id}/search"
    params = {
        "seller_id": seller_id,
        "limit": limit,
        "offset": offset,
    }

    response = requests.get(
        url,
        headers=self.headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()