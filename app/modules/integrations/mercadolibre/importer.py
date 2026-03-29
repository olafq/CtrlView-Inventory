from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import ExternalItem, CatalogImportRun, Channel, Product
from .client import MercadoLibreClient

def import_catalog(db: Session, run_id: int, access_token: str, seller_id: int, tenant_id: int):
    # 1. Validar la ejecución y el canal
    run = db.get(CatalogImportRun, run_id)
    if not run:
        raise Exception("Import run not found")

    # Usamos el channel_id dinámico que viene en la ejecución
    channel = db.query(Channel).filter(
        Channel.tenant_id == tenant_id, 
        Channel.type == "mercadolibre"
    ).first()
    
    if not channel:
        run.status = "failed"
        run.error = "MercadoLibre channel not found for this tenant"
        db.commit()
        return

    client = MercadoLibreClient(access_token)
    inserted = 0
    updated = 0
    offset = 0
    limit = 50

    try:
        while True:
            # 2. Buscar IDs de publicaciones (Paginado)
            search_results = client.get_item_ids(seller_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                break

            # 3. Traer detalles en bloques de 20 (Multiget para performance)
            for i in range(0, len(item_ids), 20):
                batch_ids = item_ids[i:i+20]
                items_data = client.get_items_batch(batch_ids)

                for item in items_data:
                    ext_id = item.get("id")
                    
                    # Buscar si ya existe en este canal y tenant
                    existing = db.query(ExternalItem).filter(
                        ExternalItem.tenant_id == tenant_id,
                        ExternalItem.channel_id == channel.id,
                        ExternalItem.external_item_id == ext_id
                    ).first()

                    if existing:
                        # Actualizar datos cambiantes
                        existing.stock = item.get("available_quantity", 0)
                        existing.price = item.get("price")
                        existing.status = item.get("status")
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        # Opcional: Aquí podrías crear un 'Product' en el inventario maestro si no existe
                        # Por ahora, creamos el ExternalItem vinculado
                        new_item = ExternalItem(
                            tenant_id=tenant_id,
                            product_id=None, # Aquí iría la lógica de match con Inventory maestro
                            channel_id=channel.id,
                            external_item_id=ext_id,
                            external_sku=item.get("seller_custom_field"),
                            price=item.get("price"),
                            stock=item.get("available_quantity", 0),
                            status=item.get("status"),
                            is_active=(item.get("status") == "active")
                        )
                        db.add(new_item)
                        inserted += 1

            # Control de paginación
            offset += limit
            if offset >= search_results.get("paging", {}).get("total", 0):
                break

        # 4. Finalizar reporte de la corrida
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.counts = {"inserted": inserted, "updated": updated}
        db.commit()

    except Exception as e:
        db.rollback()
        run.status = "failed"
        run.error = str(e)
        db.commit()
        raise e