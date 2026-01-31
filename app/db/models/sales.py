from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Numeric,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)

    channel_id = Column(
        Integer,
        ForeignKey("channels.id"),
        nullable=False,
    )

    external_order_id = Column(String, nullable=True, index=True)

    total_amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=True)

    created_at = Column(
    DateTime(timezone=True),
    server_default=func.now(),
    index=True,
    )


    channel = relationship("Channel")
    items = relationship(
        "StockMovement",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
