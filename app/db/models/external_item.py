from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func

from app.db.session import Base


class ExternalItem(Base):
    __tablename__ = "external_items"

    id = Column(Integer, primary_key=True, index=True)
    import_run_id = Column(Integer, ForeignKey("catalog_import_runs.id"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)

    external_id = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=True, index=True)
    title = Column(String, nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(12, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
