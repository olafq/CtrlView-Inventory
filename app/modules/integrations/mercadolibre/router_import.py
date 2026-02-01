from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.modules.integrations.mercadolibre.service_products import (
    import_products_from_ml,
)

router = APIRouter(
    prefix="/integrations/mercadolibre/import",
    tags=["MercadoLibre Import"],
)


@router.post("/products")
def import_products(
    channel_id: int = 1,
    db: Session = Depends(get_db),
):
    try:
        return import_products_from_ml(db, channel_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
