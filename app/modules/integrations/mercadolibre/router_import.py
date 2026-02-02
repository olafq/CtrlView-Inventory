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
    usando /sites/{SITE_ID}/search?seller_id=
    y las normaliza en Product + ExternalItem.
    """

    # =========================================================
    # 1️⃣ Validar canal
    # =========================================================
    channel = db.query(Channel).filter(Channel.id == channel_id).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.type != "mercadolibre":
        raise HTTPException(
            status_code=400,
            detail="Channel is not MercadoLibre",
        )

    site_id = "MLA"  # hardcoded por ahora

    # =========================================================
    # 2️⃣ Cliente ML + seller_id
    # =========================================================
    ml = get_ml_client(db, channel_id)

    me = ml.get_current_user()
    seller_id = me["id"]

    # =========================================================
    # 3️⃣ Paginación segura
    # =========================================================
    limit = 50
    offset = 0
    imported = 0

    while True:
        search = ml.search_items_by_seller(
            site_id=site_id,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )

        results = search.get("results", [])

        if not results:
            break

        for item in results:
            external_item_id = item["id"]
            title = item.get("title")
            price = item.get("price", 0)
            available_qty = item.get("available_quantity", 0)
            status = item.get("status")

            # SKU: usamos seller_custom_field si existe
            sku = (
                item.get("seller_custom_field")
                or external_item_id
            )

            # =================================================
            # PRODUCT (madre)
            # =================================================
            product = (
                db.query(Product)
                .filter(Product.sku == sku)
                .first()
            )

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

            # =================================================
            # EXTERNAL ITEM (canal)
            # =================================================
            external = (
                db.query(ExternalItem)
                .filter(
                    ExternalItem.channel_id == channel.id,
                    ExternalItem.external_item_id == external_item_id,
                )
                .first()
            )

            if not external:
                external = ExternalItem(
                    product_id=product.id,
                    channel_id=channel.id,
                    external_item_id=external_item_id,
                    external_sku=sku,
                    price=price,
                    stock=available_qty,
                    status=status,
                    raw_payload=item,
                )
                db.add(external)
            else:
                # Sync liviano (idempotente)
                external.price = price
                external.stock = available_qty
                external.status = status
                external.raw_payload = item

            imported += 1

        db.commit()

        offset += len(results)

        if len(results) < limit:
            break

    return {
        "channel_id": channel_id,
        "seller_id": seller_id,
        "items_imported": imported,
    }
