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

    # 2️⃣ Cliente ML (con token válido)
    ml = get_ml_client(db, channel_id)

    # 3️⃣ Obtener seller
    me = ml.get_current_user()
    seller_id = me["id"]

    imported = 0
    offset = 0
    limit = 50

    # 4️⃣ Paginación real
    while True:
        search = ml.get_item_ids(
            user_id=seller_id,
            limit=limit,
            offset=offset,
        )

        item_ids = search.get("results", [])
        if not item_ids:
            break

        for item_id in item_ids:
            item = ml.get_item_detail(item_id)

            sku = item.get("seller_custom_field") or item_id
            title = item.get("title")
            price = item.get("price", 0)
            available_qty = item.get("available_quantity", 0)

            # PRODUCT (normalizado)
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

            # EXTERNAL ITEM (MercadoLibre)
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

        offset += limit

    db.commit()

    return {
        "channel_id": channel_id,
        "items_imported": imported,
    }
