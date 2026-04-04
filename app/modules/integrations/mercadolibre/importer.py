from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import ExternalItem, CatalogImportRun, Channel, MercadoLibreAuth
from .service import get_ml_client 

def import_mercadolibre_items(db: Session, auth: MercadoLibreAuth, run_id: int):
    """
    Sincronización de producción:
    1. Usa el cliente con Auto-Refresh para evitar errores de Token.
    2. Maneja lotes (batches) de 20 para cumplir con Mercado Libre.
    3. Blindaje de datos: Evita que precios o SKUs nulos rompan la base de datos.
    4. Manejo de estado: Actualiza CatalogImportRun para feedback en la UI.
    """
    print(f"🚀 [IMPORT] Iniciando proceso para Run ID: {run_id}")

    # 1. Obtener el registro de la corrida (Usamos query para mayor compatibilidad)
    run = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
    if not run:
        print(f"❌ [ERROR] No se encontró CatalogImportRun con ID {run_id}")
        return

    try:
        # Parámetros desde el objeto auth
        tenant_id = auth.tenant_id
        channel_id = auth.channel_id
        seller_id = auth.ml_user_id

        # 2. Configuración de API
        # get_ml_client asegura que si el token venció, se refresque antes de empezar
        client = get_ml_client(db, channel_id=channel_id, tenant_id=tenant_id)
        
        inserted = 0
        updated = 0
        offset = 0
        limit = 50

        run.status = "processing"
        db.commit()

        while True:
            # 3. Buscar IDs de publicaciones del vendedor
            search_results = client.get_item_ids(seller_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                break

            # 4. Multiget de a 20 items (Recomendación oficial de ML)
            for i in range(0, len(item_ids), 20):
                batch_ids = item_ids[i:i+20]
                items_data = client.get_items_batch(batch_ids)

                for item in items_data:
                    # Validar si ML devolvió error para este ítem específico dentro del batch
                    item_body = item.get("body", {}) if "body" in item else item
                    if item.get("code") and item.get("code") != 200:
                        continue

                    ext_id = item_body.get("id")
                    if not ext_id:
                        continue
                    
                    # --- MAPEO SEGURO DE DATOS (El "Blindaje") ---
                    # Si el precio es None, lo ponemos en 0.0 para que la DB no lo rechace
                    raw_price = item_body.get("price")
                    price = float(raw_price) if raw_price is not None else 0.0
                    
                    stock = item_body.get("available_quantity", 0)
                    status = item_body.get("status", "closed")
                    
                    # Si no hay SKU (seller_custom_field), usamos el ID de ML para no dejarlo nulo
                    sku = item_body.get("seller_custom_field") or ext_id

                    # 5. Upsert: Buscar si ya existe para actualizar o crear
                    existing = db.query(ExternalItem).filter(
                        ExternalItem.channel_id == channel_id,
                        ExternalItem.external_item_id == ext_id
                    ).first()

                    if existing:
                        existing.stock = stock
                        existing.price = price
                        existing.status = status
                        existing.external_sku = sku
                        existing.is_active = (status == "active")
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        new_item = ExternalItem(
                            tenant_id=tenant_id,
                            channel_id=channel_id,
                            external_item_id=ext_id,
                            external_sku=sku,
                            price=price,
                            stock=stock,
                            status=status,
                            is_active=(status == "active"),
                            updated_at=datetime.utcnow()
                        )
                        db.add(new_item)
                        inserted += 1

                # Commit parcial por lote de 20: Si el siguiente lote falla, ya guardamos estos
                db.commit()

            # Control de paginación
            offset += limit
            total_items = search_results.get("paging", {}).get("total", 0)
            if offset >= total_items:
                break

        # 6. Finalización exitosa
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Completado: {inserted} nuevos, {updated} actualizados."
        db.commit()
        
        print(f"✅ [IMPORT] Finalizado: {inserted} insertados, {updated} actualizados.")

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"🔥 [CRITICAL] Error en importer: {error_msg}")
        
        # Intentamos marcar el fallo para que el usuario lo vea en la UI
        try:
            # Re-buscamos el run por si la sesión se perdió
            run_error = db.query(CatalogImportRun).filter(CatalogImportRun.id == run_id).first()
            if run_error:
                run_error.status = "failed"
                run_error.error = f"Error crítico: {error_msg}"
                run_error.finished_at = datetime.utcnow()
                db.commit()
        except Exception as e_db:
            print(f"No se pudo guardar el error en DB: {e_db}")