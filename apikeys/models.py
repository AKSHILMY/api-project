import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class Base(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)


class Organization(Base):
    id: uuid.UUID
    name: str
    created_at: datetime


class Project(Base):
    id: uuid.UUID
    name: str
    org_id: uuid.UUID
    created_at: datetime


class Product(Base):
    id: uuid.UUID
    name: str
    org_id: uuid.UUID
    created_at: datetime


class KeyMetadata(Base):
    name: Optional[str] = None
    scopes: list[str] = []
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    custom: dict[str, Any] = {}


class APIKey(Base):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    key_prefix: str
    metadata: KeyMetadata
    revoked_at: Optional[datetime]
    created_at: datetime


class APIKeyCreated(Base):
    key: APIKey
    plaintext: str
