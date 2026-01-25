from sqlalchemy.orm import Session
from app.db.models.catalog_import_run import CatalogImportRun

def get_import_run(db: Session, import_id: int) -> CatalogImportRun | None:
    return (
        db.query(CatalogImportRun)
        .filter(CatalogImportRun.id == import_id)
        .first()
    )
