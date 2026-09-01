from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    business_name: str | None = Field(default=None, max_length=160)
    document: str = Field(pattern=r"^(\d{8}|\d{11})$")
    phone: str = Field(min_length=7, max_length=30)
    address: str | None = Field(default=None, max_length=255)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    business_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
