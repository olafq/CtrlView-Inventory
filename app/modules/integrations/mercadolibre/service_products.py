import requests
from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.product import Product
from app.db.models.external_item import ExternalItem
from app.modules.integrations.mercadolibre.service import (
    get_valid_ml_access_token,
)

ML_API = "https://api.mercadolibre.com"


def import_products_from_ml(db: Session, channel_id: int) -> dict:
    """
    Import inicial de productos desde Mercado Libre.
    Crea Products + ExternalItems.
    """

    token = get_valid_ml_access_token(db, channel_id)

    # 1️⃣ Obtener seller
    me = requests.get(
        f"{ML_API}/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    me.raise_for_status()
    seller_id = me.json()["id"]

    # 2️⃣ Obtener IDs de items
    search = requests.get(
        f"{ML_API}/users/{seller_id}/items/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 50},
        timeout=10,
    )
    search.raise_for_status()
    item_ids = search.json().get("results", [])

    imported = 0

    channel = db.query(Channel).filter(Channel.id == channel_id).first()

    for external_item_id in item_ids:
        # 3️⃣ Detalle del item
        item = requests.get(
            f"{ML_API}/items/{external_item_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        item.raise_for_status()
        data = item.json()

        # 4️⃣ Resolver SKU (si no hay, usamos external_id)
        sku = (
            data.get("seller_custom_field")
            or data.get("attributes", [{}])[0].get("value_name")
            or external_item_id
        )

        product = db.query(Product).filter(Product.sku == sku).first()

        if not product:
            product = Product(
                sku=sku,
                name=data.get("title"),
                description=data.get("subtitle"),
                stock_total=int(data.get("available_quantity", 0)),
            )
            product.recalculate_available_stock()
            db.add(product)
            db.flush()  # para obtener product.id

        exists = (
            db.query(ExternalItem)
            .filter(
                ExternalItem.channel_id == channel.id,
                ExternalItem.external_item_id == external_item_id,
            )
            .first()
        )

        if not exists:
            ext = ExternalItem(
                product_id=product.id,
                channel_id=channel.id,
                external_item_id=external_item_id,
                price=data.get("price"),
                stock=int(data.get("available_quantity", 0)),
                status=data.get("status"),
                is_active=data.get("status") == "active",
            )
            db.add(ext)
            imported += 1

    db.commit()

    return {
        "seller_id": seller_id,
        "items_found": len(item_ids),
        "items_imported": imported,
    }
