from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.modules.integrations.xmercadolibre.service import (
    build_login_url,
    handle_callback,
    parse_oauth_state,
)

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
def callback(
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    if not state:
        raise HTTPException(status_code=400, detail="Missing state")

    try:
        parsed = parse_oauth_state(state)
        tenant_id = parsed["tenant_id"]
        channel_id = parsed["channel_id"]

        handle_callback(
            db=db,
            code=code,
            channel_id=channel_id,
            tenant_id=tenant_id,
        )

        frontend_url = (
            "https://ctrlview-inventory-ui.vercel.app/settings?ml=connected"
        )

        return RedirectResponse(frontend_url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# STATUS (verifica si está conectado realmente)
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

    if not auth:
        return {"connected": False}

    return {"connected": True}


# =========================================================
# DISCONNECT (Botón para desconectarse de ML)
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