from sqlalchemy.orm import Session
from app.modules.integrations.mercadolibre.importer import import_catalog


def run_import(db: Session, run_id: int):
    import_catalog(db, run_id)
