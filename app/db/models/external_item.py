from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalItem(Base):
    __tablename__ = "external_items"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_item_id = Column(String, nullable=False, index=True)
    external_sku = Column(String, nullable=True)
    external_title = Column(String, nullable=True) # <--- AGREGADO AQUÍ

    price = Column(Numeric(12, 2), nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="external_items")
    channel = relationship("Channel")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel_id",
            "external_item_id",
            name="uq_external_item_tenant_channel_item",
        ),
    )