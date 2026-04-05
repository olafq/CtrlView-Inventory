import logging
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models import ExternalItem, CatalogImportRun, MercadoLibreAuth
from .service import get_ml_client

logger = logging.getLogger(__name__)

def import_mercadolibre_items(tenant_id: int, channel_id: int, run_id: int):
    db = SessionLocal()
    try:
        run = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
        auth = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()

        if not run or not auth:
            return

        run.status = "processing"
        db.commit()

        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        
        offset = 0
        limit = 50
        total_procesados = 0

        while True:
            # Llamada a la API de ML
            search_res = client.get_item_ids(auth.ml_user_id, limit=limit, offset=offset)
            item_ids = search_res.get("results", []) # Lista de strings ["MLA1", "MLA2"...]

            if not item_ids:
                break

            for ext_id in item_ids:
                # Obtenemos el detalle de cada producto
                item_data = client.get_item_detail(ext_id)
                if not item_data:
                    continue

                # Verificamos si ya existe
                existing = db.query(ExternalItem).filter(
                    ExternalItem.channel_id == channel_id,
                    ExternalItem.external_item_id == ext_id
                ).first()

                price = float(item_data.get("price") or 0.0)
                stock = item_data.get("available_quantity", 0)
                sku = item_data.get("seller_custom_field") or ext_id

                if existing:
                    existing.price = price
                    existing.stock = stock
                    existing.status = item_data.get("status")
                    existing.updated_at = datetime.utcnow()
                else:
                    new_item = ExternalItem(
                        tenant_id=tenant_id,
                        channel_id=channel_id,
                        external_item_id=ext_id,
                        external_sku=sku,
                        price=price,
                        stock=stock,
                        status=item_data.get("status"),
                        is_active=True,
                        updated_at=datetime.utcnow()
                    )
                    db.add(new_item)
                
                total_procesados += 1

            # Commit por cada página de 50 para no perder progreso
            db.commit()

            offset += len(item_ids)
            if offset >= search_res.get("paging", {}).get("total", 0):
                break

        # Finalización exitosa
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Se sincronizaron {total_procesados} productos."
        db.commit()

    except Exception as e:
        db.rollback()
        if run:
            run.status = "failed"
            run.error = str(e)
            db.commit()
        print(f"Error en importación: {e}")
    finally:
        db.close()