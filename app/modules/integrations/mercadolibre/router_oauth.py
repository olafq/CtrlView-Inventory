from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.modules.integrations.mercadolibre.service import build_login_url, handle_callback

router = APIRouter(prefix="/integrations/mercadolibre/oauth", tags=["MercadoLibre OAuth"])

@router.get("/login")
def login(channel_id: int, db: Session = Depends(get_db)):
    try:
        url = build_login_url(db, channel_id=channel_id)
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/callback")
def callback(code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    try:
        rec = handle_callback(db, code=code, state=state)
        # ⚠️ NO devolvemos tokens crudos
        return {"ok": True, "channel_id": rec.channel_id, "ml_user_id": rec.ml_user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
