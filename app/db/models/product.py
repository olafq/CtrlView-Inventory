from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================
    # Identidad del producto
    # =========================
    sku = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # =========================
    # Negocio
    # =========================
    cost = Column(Numeric(12, 2), nullable=True)

    # =========================
    # Stock
    # =========================
    stock_total = Column(Integer, nullable=False, default=0)
    stock_reserved = Column(Integer, nullable=False, default=0)
    stock_available = Column(Integer, nullable=False, default=0)

    low_stock_threshold = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True)

    # =========================
    # Relaciones
    # =========================
    tenant = relationship("Tenant")

    external_items = relationship(
        "ExternalItem",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    # =========================
    # Metadata
    # =========================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
    )

    def recalculate_available_stock(self):
        self.stock_available = max(0, self.stock_total - self.stock_reserved)