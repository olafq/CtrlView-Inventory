from datetime import datetime
from sqlalchemy.orm import Session
import hashlib

from app.db.models import ExternalItem, CatalogImportRun, Channel


def hash_payload(payload: dict) -> str:
    return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()


def import_catalog(db: Session, run_id: int):
    run = db.get(CatalogImportRun, run_id)
    if not run:
        raise Exception("Import run not found")

    channel = db.query(Channel).filter(Channel.name == "MercadoLibre").first()
    if not channel:
        raise Exception("MercadoLibre channel not found")

    # MOCK DATA (después va API real)
    items = [
        {
            "external_item_id": "MLA-123",
            "external_variant_id": None,
            "external_sku": "REM-NIKE-M-BLK",
            "title": "Remera Nike Negra Talle M",
            "attributes": {"color": "Negro", "talle": "M"},
        },
        {
            "external_item_id": "MLA-124",
            "external_variant_id": None,
            "external_sku": "REM-NIKE-L-BLK",
            "title": "Remera Nike Negra Talle L",
            "attributes": {"color": "Negro", "talle": "L"},
        },
    ]

    inserted = 0

    for item in items:
        payload = item.copy()
        h = hash_payload(payload)

        existing = db.query(ExternalItem).filter(
            ExternalItem.channel_id == channel.id,
            ExternalItem.external_item_id == item["external_item_id"],
            ExternalItem.external_variant_id == item["external_variant_id"],
        ).first()

        if existing:
            if existing.hash != h:
                existing.raw_payload = payload
                existing.hash = h
                existing.fetched_at = datetime.utcnow()
        else:
            db.add(
                ExternalItem(
                    channel_id=channel.id,
                    external_item_id=item["external_item_id"],
                    external_variant_id=item["external_variant_id"],
                    external_sku=item["external_sku"],
                    title=item["title"],
                    attributes=item["attributes"],
                    raw_payload=payload,
                    hash=h,
                )
            )
            inserted += 1

    run.status = "success"
    run.finished_at = datetime.utcnow()
    run.counts = {"inserted": inserted}

    db.commit()
