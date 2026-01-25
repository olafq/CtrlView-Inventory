from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.catalog_import_run import CatalogImportRun
from app.api.schemas.imports import ImportRunOut

router = APIRouter(tags=["Imports"])


@router.get("/imports/{import_id}", response_model=ImportRunOut)
def get_import(import_id: int, db: Session = Depends(get_db)):
    imp = db.query(CatalogImportRun).filter(
        CatalogImportRun.id == import_id
    ).first()

    if not imp:
        raise HTTPException(status_code=404, detail="Import not found")

    return imp
