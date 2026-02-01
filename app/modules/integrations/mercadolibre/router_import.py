from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models import Product, ExternalItem, Channel
from app.modules.integrations.mercadolibre.client import get_ml_client

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre Import"],
)


@router.post("/import/products")
def import_products(
    channel_id: int,
    db: Session = Depends(get_db),
):
    """
    Importa TODAS las publicaciones (items) del vendedor de MercadoLibre
    y las normaliza en Product + ExternalItem.
    """

    # 1️⃣ Validar canal
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.type != "mercadolibre":
        raise HTTPException(status_code=400, detail="Channel is not MercadoLibre")

    ml = get_ml_client(db, channel_id)

    # 2️⃣ Obtener seller_id
    me = ml.get("/me")
    seller_id = me["id"]

    # 3️⃣ Obtener publicaciones del vendedor
    search = ml.get(f"/users/{seller_id}/items/search?limit=100")
    item_ids = search.get("results", [])

    imported = 0

    for item_id in item_ids:
        # 4️⃣ Obtener detalle del item
        item = ml.get(f"/items/{item_id}")

        sku = item.get("seller_custom_field") or item_id
        title = item.get("title")
        price = item.get("price", 0)
        available_qty = item.get("available_quantity", 0)

        # 5️⃣ PRODUCT (madre)
        product = db.query(Product).filter(Product.sku == sku).first()
        if not product:
            product = Product(
                sku=sku,
                name=title,
                stock_total=available_qty,
                stock_reserved=0,
                stock_available=available_qty,
            )
            db.add(product)
            db.flush()

        # 6️⃣ EXTERNAL ITEM (canal)
        external = (
            db.query(ExternalItem)
            .filter(
                ExternalItem.channel_id == channel.id,
                ExternalItem.external_item_id == item_id,
            )
            .first()
        )

        if not external:
            external = ExternalItem(
                product_id=product.id,
                channel_id=channel.id,
                external_item_id=item_id,
                external_sku=sku,
                price=price,
                stock=available_qty,
                status=item.get("status"),
                raw_payload=item,
            )
            db.add(external)

        imported += 1

    db.commit()

    return {
        "channel_id": channel_id,
        "items_imported": imported,
    }
