import requests
from typing import List, Dict, Any, Optional

class MercadoLibreClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # =========================
    # USER
    # =========================
    def get_current_user(self) -> Dict[str, Any]:
        """Obtiene la información del perfil del vendedor autenticado"""
        url = f"{self.BASE_URL}/users/me"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    # =========================
    # ITEMS & SEARCH
    # =========================
    def get_item_ids(
        self,
        seller_id: int,
        limit: int = 50,
        offset: int = 0,
        sort: str = "last_updated_desc"
    ) -> Dict[str, Any]:
        """
        Busca los IDs de las publicaciones del vendedor.
        Usa 'last_updated_desc' para que las novedades aparezcan primero.
        """
        url = f"{self.BASE_URL}/users/{seller_id}/items/search"
        params = {
            "limit": limit,
            "offset": offset,
            "sort": sort
        }
        r = requests.get(url, headers=self.headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_item_detail(self, item_id: str) -> Dict[str, Any]:
        """Obtiene el detalle completo de un ítem específico"""
        url = f"{self.BASE_URL}/items/{item_id}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_items_batch(self, item_ids: List[str]) -> List[Dict[str, Any]]:
        """
        OPTIMIZACIÓN: Obtiene hasta 20 ítems en una sola petición.
        Ideal para el Importer masivo.
        """
        if not item_ids:
            return []
        
        # ML permite máximo 20 IDs por multiget
        ids_str = ",".join(item_ids[:20])
        url = f"{self.BASE_URL}/items"
        params = {"ids": ids_str}
        
        r = requests.get(url, headers=self.headers, params=params, timeout=15)
        r.raise_for_status()
        
        # Mercado Libre responde con una lista de diccionarios:
        # [{'code': 200, 'body': {...}}, {'code': 404, 'body': {...}}]
        responses = r.json()
        return [res["body"] for res in responses if res.get("code") == 200]

    # =========================
    # STOCK & PRICE (UPDATES)
    # =========================
    def update_item_stock(self, item_id: str, quantity: int) -> Dict[str, Any]:
        """Actualiza el stock disponible de una publicación"""
        url = f"{self.BASE_URL}/items/{item_id}"
        payload = {"available_quantity": quantity}
        r = requests.put(url, headers=self.headers, json=payload, timeout=10)
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
    ) -> Dict[str, Any]:
        """Busca las órdenes de venta del vendedor"""
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