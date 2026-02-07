from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    DateTime,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)

    # =========================
    # Identidad del producto
    # =========================
    sku = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # =========================
    # Negocio
    # =========================
    cost = Column(Numeric(12, 2), nullable=True)

    # =========================
    # Stock (fuente de verdad)
    # =========================
    stock_total = Column(Integer, nullable=False, default=0)
    stock_reserved = Column(Integer, nullable=False, default=0)
    stock_available = Column(Integer, nullable=False, default=0)

    low_stock_threshold = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True)

    # =========================
    # Relaciones
    # =========================
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

    # =========================
    # Lógica de dominio
    # =========================
    def recalculate_available_stock(self):
        """
        Recalcula el stock disponible en base al total y reservado.
        """
        self.stock_available = max(
            0,
            self.stock_total - self.stock_reserved
        )
