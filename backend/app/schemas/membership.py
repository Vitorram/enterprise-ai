from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


MembershipRole = Literal["admin", "viewer"]


class MembershipCreate(BaseModel):
    user_id: int = Field(gt=0)
    role: MembershipRole = "viewer"


class MembershipUpdate(BaseModel):
    role: MembershipRole


class MembershipUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    organization_id: int
    role: MembershipRole
    created_at: datetime | None
    user: MembershipUserRead
