from celery import shared_task
from app.db.session import SessionLocal
from app.modules.integrations.mercadolibre.service import run_import


@shared_task
def import_mercadolibre_task(run_id: int):
    db = SessionLocal()
    try:
        run_import(db, run_id)
    finally:
        db.close()
