from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.models.sales import Sale

from app.db.session import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
    )

    sale_id = Column(
        Integer,
        ForeignKey("sales.id"),
        nullable=True,
    )

    quantity = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)  # sale, manual, sync, etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")
    sale = relationship("Sale", back_populates="items")
