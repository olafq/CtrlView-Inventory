from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Sale(Base):
    __tablename__ = "sales"

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
        index=True,
    )

    # =========================
    # External order reference
    # =========================
    external_order_id = Column(
        String,
        nullable=False,
        index=True,
    )

    # =========================
    # Estado de la orden
    # =========================
    status = Column(String, nullable=True, index=True)

    ml_last_updated = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =========================
    # Información financiera
    # =========================
    total_amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=True)

    # =========================
    # Metadata
    # =========================
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # =========================
    # Relaciones
    # =========================
    tenant = relationship("Tenant")
    channel = relationship("Channel")

    items = relationship(
        "StockMovement",
        back_populates="sale",
        cascade="all, delete-orphan",
    )

    # =========================
    # Constraints SaaS
    # =========================
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "external_order_id",
            name="uq_sales_tenant_external_order",
        ),
    )