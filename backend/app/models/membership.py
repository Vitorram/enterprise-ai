
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, UniqueConstraint
from datetime import datetime
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_memberships_user_organization",
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")
