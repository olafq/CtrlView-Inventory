from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.session import Base


class MercadoLibreAuth(Base):
    __tablename__ = "mercadolibre_auth"

    id = Column(Integer, primary_key=True, index=True)

    channel_id = Column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    ml_user_id = Column(Integer, nullable=False)

    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)

    token_type = Column(String, default="bearer")
    scope = Column(String, nullable=True)

    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    channel = relationship("Channel")

    __table_args__ = (
        UniqueConstraint("channel_id", name="uq_ml_auth_channel"),
    )
