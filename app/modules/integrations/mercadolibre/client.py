import requests


class MercadoLibreClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

    def get_current_user(self) -> dict:
        """
        Devuelve info del usuario autenticado
        """
        url = f"{self.BASE_URL}/users/me"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_item_ids(self, user_id: int, limit: int = 50, offset: int = 0) -> dict:
        """
        Devuelve IDs de publicaciones del vendedor
        """
        url = f"{self.BASE_URL}/users/{user_id}/items/search"
        params = {
            "limit": limit,
            "offset": offset,
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_item_detail(self, item_id: str) -> dict:
        """
        Devuelve el detalle completo de una publicación
        """
        url = f"{self.BASE_URL}/items/{item_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
