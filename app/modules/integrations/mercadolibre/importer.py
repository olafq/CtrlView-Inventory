from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import ExternalItem, CatalogImportRun, Channel, MercadoLibreAuth
from .service import get_ml_client 
from app.db.session import SessionLocal  # <--- Asegúrate de que esta ruta sea correcta

def import_mercadolibre_items(tenant_id: int, channel_id: int, run_id: int):
    # CREAMOS SESIÓN PROPIA PARA EL HILO DE FONDO
    db = SessionLocal()
    print(f"🚀 [IMPORT] Iniciando proceso independiente para Run ID: {run_id}")

    try:
        # Recuperamos los objetos usando la nueva sesión
        run = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
        auth = db.query(MercadoLibreAuth).filter(MercadoLibreAuth.channel_id == channel_id).first()

        if not run or not auth:
            print("❌ [ERROR] No se encontraron datos para iniciar")
            return

        run.status = "processing"
        db.commit()

        # Obtenemos el cliente (get_ml_client usará esta sesión 'db' para el refresh)
        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        seller_id = auth.ml_user_id
        
        inserted = 0
        updated = 0
        offset = 0
        limit = 50

        while True:
            search_results = client.get_item_ids(seller_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                break

            for i in range(0, len(item_ids), 20):
                batch_ids = item_ids[i:i+20]
                items_data = client.get_items_batch(batch_ids)

                for item in items_data:
                    item_body = item.get("body", {})
                    if item.get("code") != 200: continue

                    ext_id = item_body.get("id")
                    price = float(item_body.get("price") or 0.0)
                    sku = item_body.get("seller_custom_field") or ext_id

                    existing = db.query(ExternalItem).filter(
                        ExternalItem.channel_id == channel_id,
                        ExternalItem.external_item_id == ext_id
                    ).first()

                    if existing:
                        existing.stock = item_body.get("available_quantity", 0)
                        existing.price = price
                        existing.status = item_body.get("status")
                        existing.external_sku = sku
                        updated += 1
                    else:
                        new_item = ExternalItem(
                            tenant_id=tenant_id, channel_id=channel_id,
                            external_item_id=ext_id, external_sku=sku,
                            price=price, stock=item_body.get("available_quantity", 0),
                            status=item_body.get("status"), is_active=True,
                            updated_at=datetime.utcnow()
                        )
                        db.add(new_item)
                        inserted += 1

                db.commit() # Commit por cada batch de 20

            offset += limit
            if offset >= search_results.get("paging", {}).get("total", 0):
                break

        # Éxito total
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Completado: {inserted} nuevos, {updated} actualizados."
        db.commit()

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"🔥 [CRITICAL] {error_msg}")
        try:
            # Re-intentamos marcar el error en la DB
            run_err = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
            if run_err:
                run_err.status = "failed"
                run_err.error = error_msg
                run_err.finished_at = datetime.utcnow()
                db.commit()
        except:
            pass
    finally:
        db.close()