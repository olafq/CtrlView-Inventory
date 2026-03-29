import logging
from celery import shared_task
from app.db.session import SessionLocal
from app.modules.integrations.mercadolibre.importer import import_catalog

# Configuración de logs para ver el progreso en la consola de Celery
logger = logging.getLogger(__name__)

@shared_task(
    bind=True, 
    max_retries=3, 
    default_retry_delay=60,
    name="mercadolibre.import_catalog"
)
def import_mercadolibre_task(self, run_id: int, access_token: str, seller_id: int, tenant_id: int):
    """
    Tarea de Celery para importar el catálogo de Mercado Libre en segundo plano.
    """
    db = SessionLocal()
    logger.info(f"Iniciando importación ML para tenant {tenant_id} (Run: {run_id})")
    
    try:
        # Llamamos directamente al importer que configuramos
        import_catalog(
            db=db,
            run_id=run_id,
            access_token=access_token,
            seller_id=seller_id,
            tenant_id=tenant_id
        )
        logger.info(f"Importación exitosa para run_id {run_id}")
        
    except Exception as exc:
        logger.error(f"Error en tarea de importación: {str(exc)}")
        # Si falla por algo temporal, reintenta la tarea
        db.rollback()
        raise self.retry(exc=exc)
        
    finally:
        db.close()