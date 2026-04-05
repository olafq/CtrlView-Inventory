from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.db.models import CatalogImportRun, Channel, MercadoLibreAuth
from .importer import import_mercadolibre_items
from datetime import datetime

router = APIRouter(prefix="/integrations/mercadolibre", tags=["MercadoLibre"])

@router.post("/import/start")
def start_import(tenant_id: int, channel_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Validar que existe el canal y auth (Prevención de errores)
    auth = db.query(MercadoLibreAuth).filter_by(channel_id=channel_id).first()
    if not auth:
        return {"status": "error", "message": "No hay credenciales para este canal."}

    # 2. Crear la corrida
    run = CatalogImportRun(
        tenant_id=tenant_id,
        channel_id=channel_id,
        status="pending",
        started_at=datetime.utcnow()
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # 3. Disparar tarea pasando SOLO IDs
    background_tasks.add_task(import_mercadolibre_items, tenant_id, channel_id, run.id)
    
    return {"status": "import_started", "run_id": run.id}

@router.get("/import/latest")
def get_latest_import(tenant_id: int, channel_id: int, db: Session = Depends(get_db)):
    run = db.query(CatalogImportRun).filter(
        CatalogImportRun.tenant_id == tenant_id,
        CatalogImportRun.channel_id == channel_id
    ).order_by(CatalogImportRun.id.desc()).first()
    
    if not run:
        return {"status": "none"}
    
    # Retorno manual para evitar el error 500 de sesión cerrada
    return {
        "run_id": run.id,
        "status": run.status,
        "message": run.error or "Sin detalles",
        "started_at": run.started_at.isoformat() if run.started_at else None
    }