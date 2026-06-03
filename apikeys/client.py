import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import crypto
from .db.models import APIKeyRecord, OrgRecord, ProductRecord, ProjectProductRecord, ProjectRecord, RateLimitCounter
from .db.session import make_session_factory
from .exceptions import (
    AlreadyExistsError,
    APIKeyError,
    ExpiredKeyError,
    InsufficientScopeError,
    InvalidKeyError,
    QuotaError,
    RevokedKeyError,
)
from .models import APIKey, APIKeyCreated, KeyMetadata, KeyStatus, Organization, Product, Project, RateLimitWindow


class APIKeyClient:
    def __init__(
        self,
        db_url: Optional[str] = None,
        *,
        signing_secret: str,
        key_prefix: str = "sk",
        environment: str = "",
        _sessions: Optional[async_sessionmaker[AsyncSession]] = None,
    ) -> None:
        if not signing_secret:
            raise ValueError("signing_secret is required and must not be empty")
        self._secret = signing_secret
        self._key_prefix = key_prefix
        self._environment = environment
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
            try:
                await s.commit()
            except IntegrityError:
                await s.rollback()
                existing = (await s.execute(
                    select(OrgRecord).where(OrgRecord.name == name)
                )).scalar_one_or_none()
                raise AlreadyExistsError(
                    f"Organization {name!r} already exists",
                    existing_id=str(existing.id) if existing else None,
                )
            await s.refresh(record)
            return _org(record)

    async def get_or_create_organization(self, name: str) -> tuple[Organization, bool]:
        try:
            org = await self.create_organization(name)
            return org, True
        except AlreadyExistsError as e:
            async with self._sessions() as s:
                record = (await s.execute(
                    select(OrgRecord).where(OrgRecord.name == name)
                )).scalar_one()
            return _org(record), False

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
            try:
                await s.commit()
            except IntegrityError:
                await s.rollback()
                existing = (await s.execute(
                    select(ProjectRecord).where(
                        ProjectRecord.org_id == uuid.UUID(org_id),
                        ProjectRecord.name == name,
                    )
                )).scalar_one_or_none()
                raise AlreadyExistsError(
                    f"Project {name!r} already exists in this organization",
                    existing_id=str(existing.id) if existing else None,
                )
            await s.refresh(record)
            return _project(record)

    async def get_or_create_project(self, org_id: str, name: str) -> tuple[Project, bool]:
        try:
            project = await self.create_project(org_id, name)
            return project, True
        except AlreadyExistsError:
            async with self._sessions() as s:
                record = (await s.execute(
                    select(ProjectRecord).where(
                        ProjectRecord.org_id == uuid.UUID(org_id),
                        ProjectRecord.name == name,
                    )
                )).scalar_one()
            return _project(record), False

    async def create_product(self, org_id: str, name: str) -> Product:
        await _require_org(self._sessions, org_id)
        async with self._sessions() as s:
            record = ProductRecord(name=name, org_id=uuid.UUID(org_id))
            s.add(record)
            try:
                await s.commit()
            except IntegrityError:
                await s.rollback()
                existing = (await s.execute(
                    select(ProductRecord).where(
                        ProductRecord.org_id == uuid.UUID(org_id),
                        ProductRecord.name == name,
                    )
                )).scalar_one_or_none()
                raise AlreadyExistsError(
                    f"Product {name!r} already exists in this organization",
                    existing_id=str(existing.id) if existing else None,
                )
            await s.refresh(record)
            return _product(record)

    async def get_or_create_product(self, org_id: str, name: str) -> tuple[Product, bool]:
        try:
            product = await self.create_product(org_id, name)
            return product, True
        except AlreadyExistsError:
            async with self._sessions() as s:
                record = (await s.execute(
                    select(ProductRecord).where(
                        ProductRecord.org_id == uuid.UUID(org_id),
                        ProductRecord.name == name,
                    )
                )).scalar_one()
            return _product(record), False

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

            plaintext, key_prefix, key_hash = crypto.generate_key(
                prefix=self._key_prefix,
                environment=self._environment,
                secret=self._secret,
            )
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

    async def delete_key(self, key_id: str) -> None:
        """Permanently erase the key record. Cannot be undone. No audit trail is kept.
        Use revoke_key() instead to disable a key while preserving the audit record."""
        async with self._sessions() as s:
            result = await s.execute(
                delete(APIKeyRecord).where(APIKeyRecord.id == uuid.UUID(key_id))
            )
            if result.rowcount == 0:
                raise APIKeyError(f"Key {key_id!r} not found")
            await s.commit()

    async def update_key(self, key_id: str, *, metadata: KeyMetadata) -> APIKey:
        """Replace the metadata on an existing key in-place."""
        async with self._sessions() as s:
            record = await s.get(APIKeyRecord, uuid.UUID(key_id))
            if record is None:
                raise APIKeyError(f"Key {key_id!r} not found")
            record.key_meta = metadata.model_dump(mode="json")
            await s.commit()
            await s.refresh(record)
            return _api_key(record)

    async def verify_key(self, plaintext_key: str, *, track_usage: bool = True) -> APIKey:
        try:
            prefix = crypto.extract_prefix(plaintext_key)
        except ValueError:
            raise InvalidKeyError("Malformed key format")

        candidate_hash = crypto.hash_key(plaintext_key, self._secret)

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
                raise ExpiredKeyError("Key has expired", expired_at=meta.expires_at)

            if track_usage:
                record.last_used_at = datetime.now(timezone.utc)
                record.use_count = (record.use_count or 0) + 1
                await s.commit()
                await s.refresh(record)

            return _api_key(record)

    async def validate_key(
        self,
        plaintext_key: str,
        *,
        org_id: Optional[str] = None,
        project_id: Optional[str] = None,
        product_id: Optional[str] = None,
        required_scopes: list[str] = [],
        required_scope: Optional[str] = None,  # deprecated: use required_scopes
        check_rate_limit: bool = True,
        track_usage: bool = True,
    ) -> APIKey:
        key = await self.verify_key(plaintext_key, track_usage=track_usage)

        if org_id is not None and str(key.org_id) != org_id:
            raise InsufficientScopeError(f"Key does not belong to org {org_id!r}")

        if project_id is not None:
            if key.project_id is not None and str(key.project_id) != project_id:
                raise InsufficientScopeError(f"Key is not authorized for project {project_id!r}")

        if product_id is not None:
            if key.product_id is not None and str(key.product_id) != product_id:
                raise InsufficientScopeError(f"Key is not authorized for product {product_id!r}")

        all_scopes = list(required_scopes)
        if required_scope is not None:
            if required_scope not in all_scopes:
                all_scopes.append(required_scope)
        for scope in all_scopes:
            if scope not in key.metadata.scopes:
                raise InsufficientScopeError(f"Key does not have required scope {scope!r}")

        if check_rate_limit and key.metadata.rate_limit is not None:
            await self._check_rate_limit(key)

        return key

    async def _check_rate_limit(self, key: APIKey) -> None:
        rl = key.metadata.rate_limit
        if rl is None:
            return

        now = datetime.now(timezone.utc)
        window_start = _truncate_to_window(now, rl.window)
        window_str = rl.window.value

        async with self._sessions() as s:
            counter = (await s.execute(
                select(RateLimitCounter).where(
                    RateLimitCounter.key_id == key.id,
                    RateLimitCounter.window_start == window_start,
                    RateLimitCounter.window == window_str,
                )
            )).scalar_one_or_none()

            if counter is None:
                counter = RateLimitCounter(
                    key_id=key.id,
                    window_start=window_start,
                    window=window_str,
                    count=1,
                )
                s.add(counter)
                try:
                    await s.commit()
                except IntegrityError:
                    # Concurrent insert won the race; re-fetch and increment
                    await s.rollback()
                    counter = (await s.execute(
                        select(RateLimitCounter).where(
                            RateLimitCounter.key_id == key.id,
                            RateLimitCounter.window_start == window_start,
                            RateLimitCounter.window == window_str,
                        )
                    )).scalar_one()
                    counter.count += 1
                    await s.commit()
            else:
                counter.count += 1
                await s.commit()

            if counter.count > rl.requests:
                raise QuotaError(
                    "Rate limit exceeded",
                    retry_after_seconds=_seconds_until_next_window(now, rl.window),
                )

    async def get_key(self, key_id: str) -> APIKey:
        async with self._sessions() as s:
            record = await s.get(APIKeyRecord, uuid.UUID(key_id))
            if record is None:
                raise APIKeyError(f"Key {key_id!r} not found")
            return _api_key(record)

    async def list_org_keys(self, org_id: str, *, status: KeyStatus = KeyStatus.all) -> list[APIKey]:
        async with self._sessions() as s:
            stmt = select(APIKeyRecord).where(APIKeyRecord.org_id == uuid.UUID(org_id))
            stmt = _apply_sql_status_filter(stmt, status)
            rows = (await s.execute(stmt)).scalars().all()
            return _filter_keys_by_status([_api_key(r) for r in rows], status)

    async def list_project_keys(self, project_id: str, *, status: KeyStatus = KeyStatus.all) -> list[APIKey]:
        async with self._sessions() as s:
            stmt = select(APIKeyRecord).where(APIKeyRecord.project_id == uuid.UUID(project_id))
            stmt = _apply_sql_status_filter(stmt, status)
            rows = (await s.execute(stmt)).scalars().all()
            return _filter_keys_by_status([_api_key(r) for r in rows], status)

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


# --- helpers ---

def _truncate_to_window(dt: datetime, window: RateLimitWindow) -> datetime:
    if window == RateLimitWindow.second:
        return dt.replace(microsecond=0)
    if window == RateLimitWindow.minute:
        return dt.replace(second=0, microsecond=0)
    if window == RateLimitWindow.hour:
        return dt.replace(minute=0, second=0, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)  # day


def _seconds_until_next_window(now: datetime, window: RateLimitWindow) -> int:
    ws = _truncate_to_window(now, window)
    deltas = {
        RateLimitWindow.second: timedelta(seconds=1),
        RateLimitWindow.minute: timedelta(minutes=1),
        RateLimitWindow.hour: timedelta(hours=1),
        RateLimitWindow.day: timedelta(days=1),
    }
    next_ws = ws + deltas[window]
    return max(1, int((next_ws - now).total_seconds()) + 1)


def _apply_sql_status_filter(stmt, status: KeyStatus):
    # Only revoked can be filtered purely in SQL; active/expired also need Python post-filtering
    # because expires_at lives in the JSON metadata column.
    if status == KeyStatus.revoked:
        stmt = stmt.where(APIKeyRecord.revoked_at.isnot(None))
    elif status in (KeyStatus.active, KeyStatus.expired):
        # Exclude already-revoked rows for both active and expired
        stmt = stmt.where(APIKeyRecord.revoked_at.is_(None))
    return stmt


def _filter_keys_by_status(keys: list[APIKey], status: KeyStatus) -> list[APIKey]:
    if status == KeyStatus.all or status == KeyStatus.revoked:
        return keys
    now = datetime.now(timezone.utc)
    if status == KeyStatus.active:
        return [k for k in keys if k.metadata.expires_at is None or k.metadata.expires_at >= now]
    if status == KeyStatus.expired:
        return [k for k in keys if k.metadata.expires_at is not None and k.metadata.expires_at < now]
    return keys


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
        last_used_at=r.last_used_at,
        use_count=r.use_count or 0,
    )


async def _require_org(sessions: async_sessionmaker, org_id: str) -> None:
    async with sessions() as s:
        if not await s.get(OrgRecord, uuid.UUID(org_id)):
            raise APIKeyError(f"Organization {org_id!r} not found")
