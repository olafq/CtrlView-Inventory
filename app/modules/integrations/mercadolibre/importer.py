import logging
from datetime import datetime
from app.db.session import SessionLocal 
from app.db.models import ExternalItem, CatalogImportRun, MercadoLibreAuth
from .service import get_ml_client

logger = logging.getLogger(__name__)

def import_mercadolibre_items(tenant_id: int, channel_id: int, run_id: int):
    # Sesión local única para el hilo de fondo (evita errores de conexión cerrada)
    db = SessionLocal()
    try:
        # 1. Obtenemos la corrida y la autenticación dinámicamente
        run = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
        auth = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()

        if not run or not auth:
            logger.error(f"Faltan datos: Run {run_id}, Auth para Canal {channel_id}")
            return

        # 2. Marcamos inicio de procesamiento
        run.status = "processing"
        db.commit()

        # 3. Cliente de ML dinámico
        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        
        # 4. Buscamos los productos usando el ml_user_id de la base de datos (NADA MANUAL)
        search_res = client.get_item_ids(auth.ml_user_id) 
        item_ids = search_res.get("results", [])

        total_procesados = 0
        
        # 5. Loop de procesamiento de los 44 (o los que haya)
        for ext_id in item_ids:
            item_data = client.get_item_detail(ext_id)
            if not item_data: continue

            # Buscamos si ya existe para actualizar o crear
            existing = db.query(ExternalItem).filter(
                ExternalItem.channel_id == channel_id,
                ExternalItem.external_item_id == ext_id
            ).first()

            # Mapeo de campos dinámicos
            item_fields = {
                "tenant_id": tenant_id,
                "channel_id": channel_id,
                "external_item_id": ext_id,
                "external_sku": item_data.get("seller_custom_field") or ext_id,
                "price": float(item_data.get("price") or 0.0),
                "stock": item_data.get("available_quantity", 0),
                "status": item_data.get("status"),
                "is_active": True,
                "updated_at": datetime.utcnow()
            }

            if existing:
                for key, value in item_fields.items():
                    setattr(existing, key, value)
            else:
                db.add(ExternalItem(**item_fields))
            
            total_procesados += 1

        # 6. Finalización exitosa
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Sincronización terminada: {total_procesados} productos."
        db.commit()

    except Exception as e:
        db.rollback()
        # Captura el error real para que lo veas en el dashboard de Supabase
        run_error = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
        if run_error:
            run_error.status = "failed"
            run_error.error = str(e)
            db.commit()
        logger.error(f"Error en importador: {str(e)}")
    finally:
        db.close()