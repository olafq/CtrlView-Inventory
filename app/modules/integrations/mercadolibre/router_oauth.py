from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.models.mercadolibre_auth import MercadoLibreAuth
from app.modules.integrations.mercadolibre.service import (
    build_login_url,
    handle_callback,
)

router = APIRouter(
    prefix="/integrations/mercadolibre/oauth",
    tags=["MercadoLibre OAuth"],
)


# =========================================================
# LOGIN (redirige a MercadoLibre)
# =========================================================
@router.get("/login")
def login(channel_id: int, db: Session = Depends(get_db)):
    try:
        url = build_login_url(db, channel_id=channel_id)
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# CALLBACK (MercadoLibre vuelve acá)
# =========================================================
@router.get("/callback")
def callback(code: str | None = None, db: Session = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    try:
        rec = handle_callback(db, code=code)

        # 🔥 Redirige automáticamente al frontend
        frontend_url = (
            "http://localhost:3000/settings?ml=connected"
        )

        return RedirectResponse(frontend_url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# STATUS (verifica si está conectado realmente)
# =========================================================
@router.get("/status")
def status(channel_id: int, db: Session = Depends(get_db)):

    auth = (
        db.query(MercadoLibreAuth)
        .filter(MercadoLibreAuth.channel_id == channel_id)
        .first()
    )

    if not auth:
        return {"connected": False}

    return {"connected": True}
