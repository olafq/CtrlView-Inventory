from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import ExternalItem, CatalogImportRun, Channel
from .client import MercadoLibreClient

def import_mercadolibre_items(db: Session, auth, run_id: int):
    """
    Función principal para importar productos de Mercado Libre.
    Se ejecuta en segundo plano vía BackgroundTasks.
    """
    # 1. Extraemos datos del objeto auth (según tu DB de Supabase)
    tenant_id = auth.tenant_id
    access_token = auth.access_token
    seller_id = auth.ml_user_id # Usamos ml_user_id corregido
    
    # 2. Validar la ejecución
    run = db.get(CatalogImportRun, run_id)
    if not run:
        print(f"Error: Import run {run_id} no encontrado")
        return

    # Buscamos el canal de MercadoLibre para este tenant
    channel = db.query(Channel).filter(
        Channel.tenant_id == tenant_id, 
        Channel.type == "mercadolibre"
    ).first()
    
    if not channel:
        run.status = "failed"
        run.error = "Canal MercadoLibre no encontrado para este tenant"
        db.commit()
        return

    client = MercadoLibreClient(access_token)
    inserted = 0
    updated = 0
    offset = 0
    limit = 50

    try:
        run.status = "processing"
        db.commit()

        while True:
            # 3. Buscar IDs de publicaciones (Paginado)
            search_results = client.get_item_ids(seller_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                break

            # 4. Traer detalles en bloques (Multiget)
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

                    # Mapeo de datos básicos
                    stock = item.get("available_quantity", 0)
                    price = item.get("price")
                    status = item.get("status")

                    if existing:
                        existing.stock = stock
                        existing.price = price
                        existing.status = status
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        new_item = ExternalItem(
                            tenant_id=tenant_id,
                            product_id=None, 
                            channel_id=channel.id,
                            external_item_id=ext_id,
                            external_sku=item.get("seller_custom_field"),
                            price=price,
                            stock=stock,
                            status=status,
                            is_active=(status == "active")
                        )
                        db.add(new_item)
                        inserted += 1

                # Commit parcial por lote para no saturar la conexión
                db.commit()

            # Control de paginación
            offset += limit
            paging = search_results.get("paging", {})
            if offset >= paging.get("total", 0):
                break

        # 5. Finalizar reporte exitoso
        run.status = "success"
        run.finished_at = datetime.utcnow()
        # Guardamos el conteo final
        run.error = f"Insertados: {inserted}, Actualizados: {updated}" 
        db.commit()
        print(f"Importación exitosa para tenant {tenant_id}: {inserted} nuevos.")

    except Exception as e:
        db.rollback()
        run.status = "failed"
        run.error = str(e)
        db.commit()
        print(f"Error en importación: {str(e)}")