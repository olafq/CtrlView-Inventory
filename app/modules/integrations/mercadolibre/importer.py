import logging
from datetime import datetime
from app.db.session import SessionLocal 
from app.db.models import ExternalItem, CatalogImportRun, MercadoLibreAuth
from .service import get_ml_client

logger = logging.getLogger(__name__)

def import_mercadolibre_items(tenant_id: int, channel_id: int, run_id: int):
    # 1. Abrimos una sesión nueva exclusiva para este hilo de fondo
    db = SessionLocal()
    try:
        # 2. Obtenemos la corrida y la autenticación dinámicamente
        run = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
        auth = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()

        if not run or not auth:
            logger.error(f"Faltan datos: Run {run_id}, Auth para Canal {channel_id}")
            return

        # 3. Marcamos inicio de procesamiento y refrescamos el objeto
        run.status = "processing"
        db.commit()
        db.refresh(run) # Esto evita que el objeto 'run' expire tras el commit

        # 4. Cliente de ML dinámico (Usa el token de la DB automáticamente)
        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        
        # 5. Buscamos los productos usando el ml_user_id de la tabla (NADA MANUAL)
        search_res = client.get_item_ids(auth.ml_user_id) 
        item_ids = search_res.get("results", [])

        total_procesados = 0
        
        # 6. Loop de procesamiento de los productos encontrados
        for ext_id in item_ids:
            item_data = client.get_item_detail(ext_id)
            if not item_data:
                continue

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

        # 7. Finalización exitosa: Guardamos el TEXTO del mensaje
        run.status = "success"
        run.finished_at = datetime.utcnow()
        # ACÁ ESTABA EL ERROR: Ahora guardamos el string formateado directamente
        run.error = f"Sincronización terminada: {total_procesados} productos."
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error en importador: {str(e)}")
        # 8. Captura el error real para que lo veas en el dashboard de Supabase
        try:
            run_error = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
            if run_error:
                run_error.status = "failed"
                run_error.error = str(e)
                db.commit()
        except Exception as db_err:
            logger.error(f"No se pudo guardar el error en DB: {str(db_err)}")
    finally:
        db.close() # Siempre cerramos la sesión manual