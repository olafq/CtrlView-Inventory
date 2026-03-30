from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import ExternalItem, CatalogImportRun, Channel
from .client import MercadoLibreClient

def import_mercadolibre_items(db: Session, auth, run_id: int):
    """
    Sincronización de producción:
    1. Usa IDs explícitos del objeto auth.
    2. Maneja lotes (batches) para respetar límites de API.
    3. Actualiza el estado de la corrida (CatalogImportRun) en tiempo real.
    """
    print(f"🚀 [IMPORT] Iniciando proceso para Run ID: {run_id}")

    try:
        # 1. Extracción segura de parámetros
        # Usamos directamente las propiedades del modelo MercadoLibreAuth
        tenant_id = auth.tenant_id
        channel_id = auth.channel_id
        access_token = auth.access_token
        seller_id = auth.ml_user_id

        # 2. Obtener el registro de la corrida
        run = db.get(CatalogImportRun, run_id)
        if not run:
            print(f"❌ [ERROR] No se encontró CatalogImportRun con ID {run_id}")
            return

        # 3. Validar canal
        channel = db.get(Channel, channel_id)
        if not channel:
            error_msg = f"Canal ID {channel_id} no encontrado."
            print(f"❌ [ERROR] {error_msg}")
            run.status = "failed"
            run.error = error_msg
            db.commit()
            return

        # 4. Configuración de API y contadores
        client = MercadoLibreClient(access_token)
        inserted = 0
        updated = 0
        offset = 0
        limit = 50

        run.status = "processing"
        db.commit()

        while True:
            # Buscar IDs de publicaciones del vendedor
            search_results = client.get_item_ids(seller_id, limit=limit, offset=offset)
            item_ids = search_results.get("results", [])
            
            if not item_ids:
                break

            # API de ML recomienda multiget de a 20 items para no saturar
            for i in range(0, len(item_ids), 20):
                batch_ids = item_ids[i:i+20]
                items_data = client.get_items_batch(batch_ids)

                for item in items_data:
                    # ML a veces devuelve un wrapper con el código 200 y el body adentro
                    item_body = item.get("body", {}) if "body" in item else item
                    ext_id = item_body.get("id")
                    
                    if not ext_id:
                        continue
                    
                    # Buscar si ya existe este item en ESTE canal específico
                    existing = db.query(ExternalItem).filter(
                        ExternalItem.channel_id == channel_id,
                        ExternalItem.external_item_id == ext_id
                    ).first()

                    # Mapeo de campos
                    stock = item_body.get("available_quantity", 0)
                    price = item_body.get("price")
                    status = item_body.get("status")
                    # El SKU suele venir en seller_custom_field en ML
                    sku = item_body.get("seller_custom_field")

                    if existing:
                        existing.stock = stock
                        existing.price = price
                        existing.status = status
                        existing.external_sku = sku
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
                            is_active=(status == "active")
                        )
                        db.add(new_item)
                        inserted += 1

                # Commit parcial por lote de 20 para no perder progreso si falla el siguiente
                db.commit()

            # Control de paginación de la API de ML
            offset += limit
            total_items = search_results.get("paging", {}).get("total", 0)
            if offset >= total_items:
                break

        # 5. Finalización exitosa
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.error = f"Completado. {inserted} nuevos, {updated} actualizados."
        db.commit()
        
        print(f"✅ [IMPORT] Finalizado: {inserted} insertados, {updated} actualizados.")

    except Exception as e:
        db.rollback()
        error_msg = f"Error crítico: {str(e)}"
        print(f"🔥 [CRITICAL] {error_msg}")
        
        # Intentamos marcar el fallo en la base de datos
        try:
            run = db.get(CatalogImportRun, run_id)
            if run:
                run.status = "failed"
                run.error = error_msg
                db.commit()
        except:
            pass