
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    cnpj = Column(String(14), unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


    memberships = relationship("Membership", back_populates="organization")
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"
