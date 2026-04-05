from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.db.dependencies import get_db
from app.db.models import Channel, CatalogImportRun, ExternalItem, MercadoLibreAuth
# Importamos la función que ejecutará la carga en segundo plano
from .importer import import_mercadolibre_items

router = APIRouter(
    prefix="/integrations/mercadolibre",
    tags=["MercadoLibre"]
)

# =========================================================
# 1. LISTADO DE PRODUCTOS (Consumido por el Frontend)
# =========================================================
@router.get("/items")
def get_ml_items(
    tenant_id: int,
    channel_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Retorna los ítems de ML ya importados en la DB.
    """
    items = db.query(ExternalItem).filter(
        ExternalItem.tenant_id == tenant_id,
        ExternalItem.channel_id == channel_id
    ).order_by(ExternalItem.updated_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": item.id,
            "external_id": item.external_item_id,
            "sku": item.external_sku or "N/A",
            "price": float(item.price) if item.price else 0.0,
            "stock": item.stock or 0,
            "status": item.status or "unknown",
            "is_active": item.is_active,
            "updated_at": item.updated_at
        } for item in items
    ]

# =========================================================
# 2. DISPARADOR DE IMPORTACIÓN (Background Task)
# =========================================================
@router.post("/import/start")
def start_import(
    tenant_id: int,
    channel_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Validar existencia del canal
    channel = db.query(Channel).filter(
        Channel.id == channel_id, 
        Channel.tenant_id == tenant_id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    # 2. Validar credenciales
    auth = db.query(MercadoLibreAuth).filter(
        MercadoLibreAuth.channel_id == channel_id
    ).first()

    if not auth:
        raise HTTPException(status_code=401, detail="Cuenta no vinculada")

    # 3. Crear registro de la corrida
    run = CatalogImportRun(
        tenant_id=tenant_id,
        channel_id=channel_id,
        status="pending",
        started_at=datetime.utcnow()
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 4. LANZAR TAREA (Solo pasamos IDs, no la sesión db)
    background_tasks.add_task(
        import_mercadolibre_items,
        tenant_id=tenant_id,
        channel_id=channel_id,
        run_id=run.id
    )

    return {"status": "import_started", "run_id": run.id}

# =========================================================
# 3. MONITOREO DE ESTADO (Evita el Error 500)
# =========================================================
@router.get("/import/latest")
def get_latest_import(tenant_id: int, channel_id: int, db: Session = Depends(get_db)):
    """
    Retorna la última corrida. Versión blindada contra Error 500.
    """
    run = db.query(CatalogImportRun).filter(
        CatalogImportRun.tenant_id == tenant_id,
        CatalogImportRun.channel_id == channel_id
    ).order_by(CatalogImportRun.started_at.desc()).first()
    
    if not run:
        return {"status": "none", "message": "No hay importaciones previas."}
    
    # IMPORTANTE: Extraemos los valores manualmente para que FastAPI no explote
    return {
        "run_id": int(run.id),
        "status": str(run.status),
        "message": str(run.error) if run.error else "Sin detalles adicionales.",
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None
    }