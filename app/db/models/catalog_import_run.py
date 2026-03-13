from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from datetime import datetime
from sqlalchemy.orm import relationship

from app.db.session import Base


class CatalogImportRun(Base):
    __tablename__ = "catalog_import_runs"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant")
    channel = relationship("Channel")