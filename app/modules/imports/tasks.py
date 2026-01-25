from datetime import datetime
import time

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.catalog_import_run import CatalogImportRun
from app.db.models.external_item import ExternalItem


@celery_app.task(bind=True)
def run_import(import_id: int):
    db = SessionLocal()
    try:
        run = db.get(CatalogImportRun, import_id)
        if not run:
            return {"ok": False, "reason": "import not found"}

        # running
        run.status = "running"
        db.commit()

        # simulamos trabajo (como si llamáramos a MercadoLibre)
        time.sleep(2)

        # mock items
        mock_items = [
            {"external_id": "MLA-1001", "sku": "SKU-1001", "title": "Producto 1001", "stock": 10, "price": 1000},
            {"external_id": "MLA-1002", "sku": "SKU-1002", "title": "Producto 1002", "stock": 5, "price": 2500},
            {"external_id": "MLA-1003", "sku": "SKU-1003", "title": "Producto 1003", "stock": 0, "price": 999},
        ]

        for it in mock_items:
            db.add(
                ExternalItem(
                    import_run_id=run.id,
                    channel_id=run.channel_id,
                    external_id=it["external_id"],
                    sku=it["sku"],
                    title=it["title"],
                    stock=it["stock"],
                    price=it["price"],
                )
            )

        # finished
        run.status = "finished"
        run.finished_at = datetime.utcnow()
        run.error = None
        db.commit()

        return {"ok": True, "items": len(mock_items)}

    except Exception as e:
        run.status = "failed"
        run.error = str(e)
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()
