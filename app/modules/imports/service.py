from sqlalchemy.orm import Session
from app.db.models import CatalogImportRun, Channel

def create_import_run(db: Session, channel_id: int) -> CatalogImportRun:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise ValueError("Channel not found")

    run = CatalogImportRun(channel_id=channel_id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
