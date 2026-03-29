from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import ExternalItem, CatalogImportRun, Channel
from .client import MercadoLibreClient

def import_mercadolibre_items(db: Session, auth, run_id: int):
    """
    Función principal para importar productos de Mercado Libre en segundo plano.
    Optimizado para evitar bloqueos y proporcionar logs claros en Render.
    """
    print(f"--- [DEBUG] INICIANDO IMPORTACIÓN: RUN ID {run_id} ---")

    try:
        # 1. Extraemos datos del objeto auth de forma segura
        tenant_id = getattr(auth, 'tenant_id', None)
        access_token = getattr(auth, 'access_token', None)
        seller_id = getattr(auth, 'ml_user_id', None)

        print(f"--- [DEBUG] Contexto: Tenant {tenant_id}, Seller {seller_id} ---")

        # 2. Validar la existencia del registro de ejecución
        run = db.get(CatalogImportRun, run_id)
        if not run:
            print(f"--- [ERROR] Import run {run_id} no encontrado en la DB ---")
            return

        # 3. Buscar el canal de MercadoLibre asociado
        channel = db.query(Channel).filter(
            Channel.tenant_id == tenant_id, 
            Channel.type == "mercadolibre"
        ).first()
        
        if not channel:
            print(f"--- [ERROR] Canal ML no encontrado para tenant {tenant_id} ---")
            run.status = "failed"
            run.error = "Canal MercadoLibre no encontrado para este tenant"
            db.commit()
            return

        # 4. Inicializar cliente y contadores
        client = MercadoLibreClient(access_token)
        inserted = 0
        updated = 0
        offset = 0
        limit = 50

        run.status = "processing"
        db.commit()

        while True:
            print(f"--- [DEBUG] Consultando API ML: Offset {offset} ---")
            
            # Buscar IDs de publicaciones (Paginado)
            search_results = client.get_item_ids(seller_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                print("--- [DEBUG] No se encontraron más items para procesar ---")
                break

            # 5. Traer detalles en bloques (Multiget de a 20 items según API de ML)
            for i in range(0, len(item_ids), 20):
                batch_ids = item_ids[i:i+20]
                items_data = client.get_items_batch(batch_ids)

                for item in items_data:
                    ext_id = item.get("id")
                    if not ext_id: continue
                    
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

                # Commit parcial por lote para asegurar persistencia y liberar memoria
                db.commit()

            # Control de paginación
            offset += limit
            paging = search_results.get("paging", {})
            if offset >= paging.get("total", 0):
                break

        # 6. Finalizar reporte exitoso
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Insertados: {inserted}, Actualizados: {updated}" 
        db.commit()
        
        print(f"--- [OK] IMPORTACIÓN FINALIZADA: {inserted} nuevos, {updated} actualizados ---")

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"--- [CRITICAL ERROR] --- {error_msg}")
        
        # Intentamos actualizar el estado de la corrida a fallido
        try:
            run = db.get(CatalogImportRun, run_id)
            if run:
                run.status = "failed"
                run.error = error_msg
                db.commit()
        except:
            pass