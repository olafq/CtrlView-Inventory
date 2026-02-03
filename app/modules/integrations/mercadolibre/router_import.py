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
    # 1. Canal
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel or channel.type != "mercadolibre":
        raise HTTPException(400, "Invalid MercadoLibre channel")

    ml = get_ml_client(db, channel_id)

    # 2. Seller
    me = ml.get_current_user()
    seller_id = me["id"]

    limit = 50
    offset = 0
    imported = 0

    while True:
        page = ml.get_item_ids(
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )

        item_ids = page.get("results", [])
        if not item_ids:
            break

        for item_id in item_ids:
            item = ml.get_item_detail(item_id)

            sku = item.get("seller_custom_field") or item_id
            name = item.get("title")
            price = item.get("price", 0)
            qty = item.get("available_quantity", 0)
            status = item.get("status")

            product = (
                db.query(Product)
                .filter(Product.sku == sku)
                .first()
            )

            if not product:
                product = Product(
                    sku=sku,
                    name=name,
                    stock_total=qty,
                    stock_reserved=0,
                    stock_available=qty,
                )
                db.add(product)
                db.flush()

            exists = (
                db.query(ExternalItem)
                .filter(
                    ExternalItem.channel_id == channel.id,
                    ExternalItem.external_item_id == item_id,
                )
                .first()
            )

            if not exists:
                db.add(
                    ExternalItem(
                        product_id=product.id,
                        channel_id=channel.id,
                        external_item_id=item_id,
                        external_sku=sku,
                        price=price,
                        stock=qty,
                        status=status,
                        raw_payload=item,
                    )
                )

            imported += 1

        db.commit()
        offset += len(item_ids)

        if len(item_ids) < limit:
            break

    return {
        "seller_id": seller_id,
        "items_imported": imported,
    }
