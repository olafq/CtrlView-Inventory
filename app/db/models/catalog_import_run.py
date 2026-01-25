from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from datetime import datetime
from app.db.session import Base

class CatalogImportRun(Base):
    __tablename__ = "catalog_import_runs"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
