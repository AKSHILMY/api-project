import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import crypto
from .db.models import APIKeyRecord, OrgRecord, ProductRecord, ProjectProductRecord, ProjectRecord
from .db.session import make_session_factory
from .exceptions import APIKeyError, InsufficientScopeError, InvalidKeyError, RevokedKeyError
from .models import APIKey, APIKeyCreated, KeyMetadata, Organization, Product, Project


class APIKeyClient:
    def __init__(
        self,
        db_url: Optional[str] = None,
        *,
        _sessions: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        if _sessions is not None:
            self._sessions = _sessions
        elif db_url is not None:
            self._sessions = make_session_factory(db_url)
        else:
            raise ValueError("Either db_url or _sessions must be provided")

    # --- org / project / product management ---

    async def create_organization(self, name: str) -> Organization:
        async with self._sessions() as s:
            record = OrgRecord(name=name)
            s.add(record)
            await s.commit()
            await s.refresh(record)
            return _org(record)

    async def use_organization(self, org_id: str) -> Organization:
        async with self._sessions() as s:
            record = await s.get(OrgRecord, uuid.UUID(org_id))
            if record is None:
                raise APIKeyError(f"Organization {org_id!r} not found")
            return _org(record)

    async def create_project(self, org_id: str, name: str) -> Project:
        await _require_org(self._sessions, org_id)
        async with self._sessions() as s:
            record = ProjectRecord(name=name, org_id=uuid.UUID(org_id))
            s.add(record)
            await s.commit()
            await s.refresh(record)
            return _project(record)

    async def create_product(self, org_id: str, name: str) -> Product:
        await _require_org(self._sessions, org_id)
        async with self._sessions() as s:
            record = ProductRecord(name=name, org_id=uuid.UUID(org_id))
            s.add(record)
            await s.commit()
            await s.refresh(record)
            return _product(record)

    async def add_product_to_project(self, product_id: str, project_id: str) -> None:
        async with self._sessions() as s:
            if not await s.get(ProjectRecord, uuid.UUID(project_id)):
                raise APIKeyError(f"Project {project_id!r} not found")
            if not await s.get(ProductRecord, uuid.UUID(product_id)):
                raise APIKeyError(f"Product {product_id!r} not found")
            link = ProjectProductRecord(
                project_id=uuid.UUID(project_id),
                product_id=uuid.UUID(product_id),
            )
            s.add(link)
            await s.commit()

    # --- key management ---

    async def create_key(
        self,
        org_id: str,
        *,
        project_id: Optional[str] = None,
        product_id: Optional[str] = None,
        metadata: Optional[KeyMetadata] = None,
    ) -> APIKeyCreated:
        await _require_org(self._sessions, org_id)
        async with self._sessions() as s:
            if project_id and not await s.get(ProjectRecord, uuid.UUID(project_id)):
                raise APIKeyError(f"Project {project_id!r} not found")
            if product_id and not await s.get(ProductRecord, uuid.UUID(product_id)):
                raise APIKeyError(f"Product {product_id!r} not found")

            plaintext, key_prefix, key_hash = crypto.generate_key()
            record = APIKeyRecord(
                org_id=uuid.UUID(org_id),
                project_id=uuid.UUID(project_id) if project_id else None,
                product_id=uuid.UUID(product_id) if product_id else None,
                key_prefix=key_prefix,
                key_hash=key_hash,
                key_meta=(metadata or KeyMetadata()).model_dump(mode="json"),
            )
            s.add(record)
            await s.commit()
            await s.refresh(record)
            return APIKeyCreated(key=_api_key(record), plaintext=plaintext)

    async def revoke_key(self, key_id: str) -> APIKey:
        async with self._sessions() as s:
            record = await s.get(APIKeyRecord, uuid.UUID(key_id))
            if record is None:
                raise APIKeyError(f"Key {key_id!r} not found")
            record.revoked_at = datetime.now(timezone.utc)
            await s.commit()
            await s.refresh(record)
            return _api_key(record)

    async def verify_key(self, plaintext_key: str) -> APIKey:
        try:
            prefix = crypto.extract_prefix(plaintext_key)
        except ValueError:
            raise InvalidKeyError("Malformed key format")

        candidate_hash = crypto.hash_key(plaintext_key)

        async with self._sessions() as s:
            rows = (await s.execute(
                select(APIKeyRecord).where(APIKeyRecord.key_prefix == prefix)
            )).scalars().all()

            record = next(
                (r for r in rows if crypto.keys_equal(r.key_hash, candidate_hash)),
                None,
            )
            if record is None:
                raise InvalidKeyError("Key not found")
            if record.revoked_at is not None:
                raise RevokedKeyError("Key has been revoked")

            meta = KeyMetadata.model_validate(record.key_meta)
            if meta.expires_at is not None and meta.expires_at < datetime.now(timezone.utc):
                raise InvalidKeyError("Key has expired")

            return _api_key(record)

    async def validate_key(
        self,
        plaintext_key: str,
        *,
        org_id: Optional[str] = None,
        project_id: Optional[str] = None,
        product_id: Optional[str] = None,
        required_scope: Optional[str] = None,
    ) -> APIKey:
        key = await self.verify_key(plaintext_key)

        # Org check — key must belong to the expected org
        if org_id is not None and str(key.org_id) != org_id:
            raise InsufficientScopeError(f"Key does not belong to org {org_id!r}")

        # Project check — org-wide keys (project_id=None) pass; project-scoped keys must match
        if project_id is not None:
            if key.project_id is not None and str(key.project_id) != project_id:
                raise InsufficientScopeError(f"Key is not authorized for project {project_id!r}")

        # Product check — org/project-wide keys (product_id=None) pass; product-scoped keys must match
        if product_id is not None:
            if key.product_id is not None and str(key.product_id) != product_id:
                raise InsufficientScopeError(f"Key is not authorized for product {product_id!r}")

        if required_scope is not None:
            if required_scope not in key.metadata.scopes:
                raise InsufficientScopeError(f"Key does not have required scope {required_scope!r}")

        return key

    async def get_key(self, key_id: str) -> APIKey:
        async with self._sessions() as s:
            record = await s.get(APIKeyRecord, uuid.UUID(key_id))
            if record is None:
                raise APIKeyError(f"Key {key_id!r} not found")
            return _api_key(record)

    async def list_org_keys(self, org_id: str) -> list[APIKey]:
        async with self._sessions() as s:
            rows = (await s.execute(
                select(APIKeyRecord).where(APIKeyRecord.org_id == uuid.UUID(org_id))
            )).scalars().all()
            return [_api_key(r) for r in rows]

    async def list_project_keys(self, project_id: str) -> list[APIKey]:
        async with self._sessions() as s:
            rows = (await s.execute(
                select(APIKeyRecord).where(APIKeyRecord.project_id == uuid.UUID(project_id))
            )).scalars().all()
            return [_api_key(r) for r in rows]

    async def list_organizations(self) -> list[Organization]:
        async with self._sessions() as s:
            rows = (await s.execute(select(OrgRecord))).scalars().all()
            return [_org(r) for r in rows]

    async def list_projects(self, org_id: str) -> list[Project]:
        async with self._sessions() as s:
            rows = (await s.execute(
                select(ProjectRecord).where(ProjectRecord.org_id == uuid.UUID(org_id))
            )).scalars().all()
            return [_project(r) for r in rows]

    async def list_products(self, org_id: str) -> list[Product]:
        async with self._sessions() as s:
            rows = (await s.execute(
                select(ProductRecord).where(ProductRecord.org_id == uuid.UUID(org_id))
            )).scalars().all()
            return [_product(r) for r in rows]

    async def list_project_products(self, project_id: str) -> list[Product]:
        async with self._sessions() as s:
            rows = (await s.execute(
                select(ProductRecord)
                .join(ProjectProductRecord, ProjectProductRecord.product_id == ProductRecord.id)
                .where(ProjectProductRecord.project_id == uuid.UUID(project_id))
            )).scalars().all()
            return [_product(r) for r in rows]


# --- record → Pydantic model converters ---

def _org(r: OrgRecord) -> Organization:
    return Organization(id=r.id, name=r.name, created_at=r.created_at)

def _project(r: ProjectRecord) -> Project:
    return Project(id=r.id, name=r.name, org_id=r.org_id, created_at=r.created_at)

def _product(r: ProductRecord) -> Product:
    return Product(id=r.id, name=r.name, org_id=r.org_id, created_at=r.created_at)

def _api_key(r: APIKeyRecord) -> APIKey:
    return APIKey(
        id=r.id,
        org_id=r.org_id,
        project_id=r.project_id,
        product_id=r.product_id,
        key_prefix=r.key_prefix,
        metadata=KeyMetadata.model_validate(r.key_meta),
        revoked_at=r.revoked_at,
        created_at=r.created_at,
    )



async def _require_org(sessions: async_sessionmaker, org_id: str) -> None:
    async with sessions() as s:
        if not await s.get(OrgRecord, uuid.UUID(org_id)):
            raise APIKeyError(f"Organization {org_id!r} not found")
