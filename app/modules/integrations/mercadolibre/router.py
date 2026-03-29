from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.db.dependencies import get_db
from app.db.models import Channel, CatalogImportRun, ExternalItem, MercadoLibreAuth
from app.modules.integrations.mercadolibre.tasks import import_mercadolibre_task

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre"]
)

# =========================================================
# 1. LISTADO DE PRODUCTOS (Para la Tabla del Frontend)
# =========================================================
@router.get("/items")
def get_ml_items(
    tenant_id: int,
    channel_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """
    Retorna los productos de ML ya importados en la base de datos.
    Este es el endpoint que usará tu tabla en el Frontend.
    """
    items = db.query(ExternalItem).filter(
        ExternalItem.tenant_id == tenant_id,
        ExternalItem.channel_id == channel_id
    ).offset(skip).limit(limit).all()

    return [
        {
            "id": item.id,
            "external_id": item.external_item_id,
            "sku": item.external_sku,
            "price": float(item.price) if item.price else 0,
            "stock": item.stock,
            "status": item.status,
            "is_active": item.is_active,
            "updated_at": item.updated_at
        } for item in items
    ]

# =========================================================
# 2. DISPARADOR MANUAL DE IMPORTACIÓN
# =========================================================
@router.post("/import/start")
def start_import(
    tenant_id: int,
    channel_id: int,
    db: Session = Depends(get_db)
):
    """
    Permite al usuario darle al botón 'Sincronizar' manualmente.
    """
    # Validar canal y auth
    channel = db.query(Channel).filter(
        Channel.id == channel_id, 
        Channel.tenant_id == tenant_id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado para este tenant")

    auth = db.query(MercadoLibreAuth).filter(
        MercadoLibreAuth.channel_id == channel_id
    ).first()

    if not auth:
        raise HTTPException(status_code=401, detail="Cuenta de ML no vinculada")

    # Crear el registro de la corrida
    run = CatalogImportRun(
        tenant_id=tenant_id,
        channel_id=channel.id,
        status="pending",
        started_at=datetime.utcnow()
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Disparar Celery
    import_mercadolibre_task.delay(
        run_id=run.id,
        access_token=auth.access_token,
        seller_id=int(auth.mercadolibre_user_id),
        tenant_id=tenant_id
    )

    return {"status": "import_started", "run_id": run.id}

# =========================================================
# 3. ESTADO DE LA IMPORTACIÓN (Para mostrar loaders)
# =========================================================
@router.get("/import/status/{run_id}")
def get_import_status(run_id: int, db: Session = Depends(get_db)):
    run = db.get(CatalogImportRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run no encontrado")
    
    return {
        "status": run.status,
        "counts": run.counts,
        "error": run.error,
        "finished_at": run.finished_at
    }