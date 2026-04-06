from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.db.models import CatalogImportRun
from app.modules.integrations.mercadolibre.service import (
    build_login_url,
    handle_callback,
    parse_oauth_state,
)

# IMPORTANTE: Ahora importamos la función directamente desde el importer
# en lugar de la tarea de Celery para ahorrar recursos y costos.
from app.modules.integrations.mercadolibre.importer import import_mercadolibre_items

router = APIRouter(
    prefix="/integrations/mercadolibre/oauth",
    tags=["MercadoLibre OAuth"],
)

# =========================================================
# LOGIN (redirige a MercadoLibre)
# =========================================================
@router.get("/login")
def login(
    channel_id: int,
    tenant_id: int,
    db: Session = Depends(get_db),
):
    try:
        url = build_login_url(
            db=db,
            channel_id=channel_id,
            tenant_id=tenant_id,
        )
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# CALLBACK (MercadoLibre vuelve acá)
# =========================================================
@router.get("/callback")
async def callback(
    background_tasks: BackgroundTasks, # Inyectamos BackgroundTasks de FastAPI
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    try:
        # 1. Recuperamos el contexto del estado (tenant y channel)
        parsed = parse_oauth_state(state)
        tenant_id = parsed["tenant_id"]
        channel_id = parsed["channel_id"]

        # 2. Intercambiamos el code por tokens y los guardamos en Supabase
        auth_info = handle_callback(
            db=db,
            code=code,
            channel_id=channel_id,
            tenant_id=tenant_id,
        )

        # 3. Creamos el registro de importación para el feedback visual
        new_run = CatalogImportRun(
            tenant_id=tenant_id,
            channel_id=channel_id,
            status="pending",
            started_at=datetime.utcnow()
        )
        db.add(new_run)
        db.commit()
        db.refresh(new_run)

       # 4. DISPARAMOS LA TAREA EN SEGUNDO PLANO
        # Pasamos solo IDs para que el importador abra su propia sesión db
        background_tasks.add_task(
            import_mercadolibre_items,
            tenant_id=tenant_id,
            channel_id=channel_id,
            run_id=new_run.id
        )

        # 5. Redirección final al frontend (Vercel)
        frontend_url = "https://ctrlview-inventory-ui.vercel.app/settings?ml=connected"
        return RedirectResponse(frontend_url)

    except Exception as e:
        db.rollback()
        print(f"DEBUG ERROR EN CALLBACK: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error en callback: {str(e)}")


# =========================================================
# STATUS (verifica conexión)
# =========================================================
@router.get("/status")
def status(
    channel_id: int,
    tenant_id: int,
    db: Session = Depends(get_db),
):
    auth = (
        db.query(MercadoLibreAuth)
        .filter(
            MercadoLibreAuth.channel_id == channel_id,
            MercadoLibreAuth.tenant_id == tenant_id,
        )
        .first()
    )

    return {"connected": auth is not None}


# =========================================================
# DISCONNECT (Desvincular cuenta)
# =========================================================
@router.post("/disconnect")
def disconnect(
    channel_id: int,
    tenant_id: int,
    db: Session = Depends(get_db),
):
    db.query(MercadoLibreAuth).filter(
        MercadoLibreAuth.channel_id == channel_id,
        MercadoLibreAuth.tenant_id == tenant_id,
    ).delete()

    db.commit()
    return {"ok": True}