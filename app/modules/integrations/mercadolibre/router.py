from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.db.dependencies import get_db
from app.db.models import Channel, CatalogImportRun, ExternalItem, MercadoLibreAuth, Product
# Importamos la función asíncrona que arreglamos en el paso anterior
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
    Incluye ordenamiento por actualización para ver lo más reciente arriba.
    """
    items = db.query(ExternalItem).filter(
        ExternalItem.tenant_id == tenant_id,
        ExternalItem.channel_id == channel_id
    ).order_by(ExternalItem.updated_at.desc()).offset(skip).limit(limit).all()

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
# 2. DISPARADOR DE IMPORTACIÓN (Background Task)
# =========================================================
@router.post("/import/start")
def start_import(
    tenant_id: int,
    channel_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Crea un registro en CatalogImportRun y dispara el Importer en segundo plano.
    Evita timeouts en Render y permite al usuario seguir navegando.
    """
    # Validar que el canal existe y pertenece al tenant
    channel = db.query(Channel).filter(
        Channel.id == channel_id, 
        Channel.tenant_id == tenant_id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado para este Tenant")

    # Obtener credenciales vinculadas
    auth = db.query(MercadoLibreAuth).filter(
        MercadoLibreAuth.channel_id == channel_id
    ).first()

    if not auth:
        raise HTTPException(status_code=401, detail="El canal no tiene una cuenta de ML vinculada")

    # Registrar el inicio de la corrida
    run = CatalogImportRun(
        tenant_id=tenant_id,
        channel_id=channel_id,
        status="pending",
        started_at=datetime.utcnow()
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Disparar tarea asíncrona
    background_tasks.add_task(
        import_mercadolibre_items,
        db=db,
        auth=auth,
        run_id=run.id
    )

    return {
        "status": "import_started", 
        "run_id": run.id,
        "message": "La sincronización se está ejecutando en segundo plano."
    }

# =========================================================
# 3. MONITOREO DE ESTADO
# =========================================================
@router.get("/import/latest")
def get_latest_import(tenant_id: int, channel_id: int, db: Session = Depends(get_db)):
    """Retorna la última corrida para mostrar progreso en la UI."""
    run = db.query(CatalogImportRun).filter(
        CatalogImportRun.tenant_id == tenant_id,
        CatalogImportRun.channel_id == channel_id
    ).order_by(CatalogImportRun.started_at.desc()).first()
    
    if not run:
        return {"status": "none"}
    
    return {
        "run_id": run.id,
        "status": run.status,
        "message": run.error, # Aquí guardamos el conteo de items al finalizar
        "started_at": run.started_at,
        "finished_at": run.finished_at
    }