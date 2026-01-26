from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.dependencies import get_db
from app.modules.channels.schemas import ChannelOut
from app.modules.channels.service import get_channels

router = APIRouter(prefix="/channels", tags=["Channels"])

@router.get("/", response_model=List[ChannelOut])
def list_channels(
    db: Session = Depends(get_db),
):
    return get_channels(db)
@router.post("/seed")
def seed_channels(db: Session = Depends(get_db)):
    existing = {c.name for c in db.query(Channel).all()}

    for name, ctype in [
        ("MercadoLibre", "mercadolibre"),
        ("Web", "web"),
        ("POS", "pos"),
    ]:
        if name not in existing:
            db.add(Channel(name=name, type=ctype))

    db.commit()
    return {"ok": True}
