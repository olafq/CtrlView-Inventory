from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.modules.imports.schemas import ImportRunOut
from app.modules.imports.service import create_import_run

router = APIRouter(prefix="/channels", tags=["Imports"])

@router.post("/{channel_id}/import", response_model=ImportRunOut)
def trigger_import(
    channel_id: int,
    db: Session = Depends(get_db),
):
    try:
        return create_import_run(db, channel_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Channel not found")
