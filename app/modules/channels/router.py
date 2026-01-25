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
