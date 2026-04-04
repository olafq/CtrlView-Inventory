import requests
from typing import List, Dict, Any, Optional, Callable
# Importamos la función de refresh de tu archivo oauth.py
from .oauth import refresh_access_token

class MercadoLibreClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(
        self, 
        access_token: str, 
        refresh_token: Optional[str] = None,
        on_token_refresh: Optional[Callable[[str, str], None]] = None
    ):
        """
        :param access_token: El token de acceso actual.
        :param refresh_token: El token para obtener nuevos access_tokens.
        :param on_token_refresh: Función callback que se ejecuta al refrescar. 
                                 Recibe (new_access, new_refresh).
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.on_token_refresh = on_token_refresh
        self._set_headers()

    def _set_headers(self):
        """Actualiza los headers con el access_token actual"""
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _handle_auth_error(self):
        """Proceso automático de refresh cuando el token expira"""
        if not self.refresh_token:
            raise Exception("IdentityOS Error: No se puede refrescar el token sin refresh_token.")
        
        print("🔄 MercadoLibreClient: Token expirado detectado. Iniciando Auto-Refresh...")
        try:
            # Usamos la lógica que ya tienes en oauth.py
            new_data = refresh_access_token(self.refresh_token)
            
            # Actualizamos estado interno
            self.access_token = new_data["access_token"]
            self.refresh_token = new_data["refresh_token"]
            self._set_headers()

            # Ejecutamos el callback para persistir en la DB (Supabase)
            if self.on_token_refresh:
                self.on_token_refresh(self.access_token, self.refresh_token)
                print("✅ MercadoLibreClient: Base de datos actualizada con nuevos tokens.")
                
        except Exception as e:
            print(f"❌ MercadoLibreClient: Falló el autorefresh crítico: {e}")
            raise

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Método interno que centraliza las llamadas y maneja el reintento por 401"""
        # Primer intento
        r = requests.request(method, url, headers=self.headers, **kwargs)
        
        # Si el token falló, intentamos refrescar y reintentar una única vez
        if r.status_code == 401 and self.refresh_token:
            self._handle_auth_error()
            # Segundo intento con headers actualizados
            r = requests.request(method, url, headers=self.headers, **kwargs)
        
        r.raise_for_status()
        return r

    # =========================
    # USER
    # =========================
    def get_current_user(self) -> Dict[str, Any]:
        """Obtiene la información del perfil del vendedor autenticado"""
        url = f"{self.BASE_URL}/users/me"
        return self._request("GET", url, timeout=10).json()

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
        """Busca los IDs de las publicaciones del vendedor."""
        url = f"{self.BASE_URL}/users/{seller_id}/items/search"
        params = {"limit": limit, "offset": offset, "sort": sort}
        return self._request("GET", url, params=params, timeout=10).json()

    def get_item_detail(self, item_id: str) -> Dict[str, Any]:
        """Obtiene el detalle completo de un ítem específico"""
        url = f"{self.BASE_URL}/items/{item_id}"
        return self._request("GET", url, timeout=10).json()

    def get_items_batch(self, item_ids: List[str]) -> List[Dict[str, Any]]:
        """Optimización: Obtiene hasta 20 ítems en una sola petición."""
        if not item_ids:
            return []
        
        ids_str = ",".join(item_ids[:20])
        url = f"{self.BASE_URL}/items"
        params = {"ids": ids_str}
        
        r = self._request("GET", url, params=params, timeout=15)
        responses = r.json()
        return [res["body"] for res in responses if res.get("code") == 200]

    # =========================
    # STOCK & PRICE (UPDATES)
    # =========================
    def update_item_stock(self, item_id: str, quantity: int) -> Dict[str, Any]:
        """Actualiza el stock disponible de una publicación"""
        url = f"{self.BASE_URL}/items/{item_id}"
        payload = {"available_quantity": quantity}
        return self._request("PUT", url, json=payload, timeout=10).json()

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
        return self._request("GET", url, params=params, timeout=10).json()