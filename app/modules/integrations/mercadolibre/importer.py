from datetime import datetime
from app.db.session import SessionLocal 
from app.db.models import ExternalItem, CatalogImportRun, MercadoLibreAuth
from .service import get_ml_client 

def import_mercadolibre_items(tenant_id: int, channel_id: int, run_id: int):
    db = SessionLocal()
    print(f"🚀 [IMPORTER] Iniciando Run ID: {run_id} para Channel: {channel_id}")

    try:
        # 1. Obtener la corrida
        run = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
        if not run:
            print(f"❌ [ERROR] No se encontró la corrida {run_id}")
            return

        # 2. Obtener Credenciales (Aquí es donde suele fallar)
        auth = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()
        if not auth:
            error_msg = f"No hay credenciales (MercadoLibreAuth) para el canal {channel_id}"
            print(f"❌ [ERROR] {error_msg}")
            run.status = "failed"
            run.error = error_msg
            db.commit()
            return

        run.status = "processing"
        db.commit()

        # 3. Configurar Cliente ML
        print(f"🔗 [IMPORTER] Conectando con ML para Seller: {auth.ml_user_id}")
        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        
        inserted = 0
        updated = 0
        offset = 0
        limit = 50

        # 4. Loop de Importación
        while True:
            search_results = client.get_item_ids(auth.ml_user_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                print("✅ [IMPORTER] No hay más productos para importar.")
                break

            # Procesar en batches de 20 para no saturar
            for i in range(0, len(item_ids), 20):
                batch_ids = item_ids[i:i+20]
                items_data = client.get_items_batch(batch_ids)

                for item in items_data:
                    body = item.get("body", {})
                    if item.get("code") != 200: continue

                    ext_id = body.get("id")
                    
                    # Buscar si ya existe
                    existing = db.query(ExternalItem).filter(
                        ExternalItem.channel_id == channel_id,
                        ExternalItem.external_item_id == ext_id
                    ).first()

                    if existing:
                        existing.stock = body.get("available_quantity", 0)
                        existing.price = float(body.get("price") or 0.0)
                        existing.status = body.get("status")
                        updated += 1
                    else:
                        new_item = ExternalItem(
                            tenant_id=tenant_id,
                            channel_id=channel_id,
                            external_item_id=ext_id,
                            external_sku=body.get("seller_custom_field") or ext_id,
                            price=float(body.get("price") or 0.0),
                            stock=body.get("available_quantity", 0),
                            status=body.get("status"),
                            is_active=True,
                            updated_at=datetime.utcnow()
                        )
                        db.add(new_item)
                        inserted += 1
                
                db.commit() # Guardamos el batch

            offset += limit
            if offset >= search_results.get("paging", {}).get("total", 0):
                break

        # 5. Finalizar con Éxito
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Importados: {inserted}, Actualizados: {updated}"
        db.commit()
        print(f"🏁 [IMPORTER] Finalizado con éxito. Run ID: {run_id}")

    except Exception as e:
        db.rollback()
        error_str = f"Error crítico: {str(e)}"
        print(f"🔥 [FATAL] {error_str}")
        if run:
            run.status = "failed"
            run.error = error_str
            db.commit()
    finally:
        db.close()