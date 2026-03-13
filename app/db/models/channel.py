from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)
    type = Column(String, nullable=False)

    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_channels_tenant_name"),
    )