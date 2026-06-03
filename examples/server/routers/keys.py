from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from apikeys import (
    APIKey,
    APIKeyClient,
    APIKeyCreated,
    APIKeyDepends,
    APIKeyError,
    KeyMetadata,
    KeyStatus,
    RateLimit,
    RateLimitWindow,
)
from apikeys.exceptions import AlreadyExistsError, ExpiredKeyError, InvalidKeyError, RevokedKeyError
from ..deps import get_client

router = APIRouter(tags=["keys"])

# Example protected dependency — any valid key with "read" scope
require_read = APIKeyDepends(required_scopes=["read"])


class CreateKeyBody(BaseModel):
    org_id: str
    project_id: Optional[str] = None
    product_id: Optional[str] = None
    name: Optional[str] = None
    scopes: list[str] = []
    rate_limit: Optional[RateLimit] = None
    expires_at: Optional[datetime] = None
    custom: dict = {}


class UpdateKeyBody(BaseModel):
    name: Optional[str] = None
    scopes: list[str] = []
    rate_limit: Optional[RateLimit] = None
    expires_at: Optional[datetime] = None
    custom: dict = {}


class VerifyKeyBody(BaseModel):
    key: str


@router.get("/api/orgs/{org_id}/keys", response_model=list[APIKey])
async def list_org_keys(
    org_id: str,
    status: KeyStatus = Query(KeyStatus.all),
    client: APIKeyClient = Depends(get_client),
):
    try:
        return await client.list_org_keys(org_id, status=status)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/projects/{project_id}/keys", response_model=list[APIKey])
async def list_project_keys(
    project_id: str,
    status: KeyStatus = Query(KeyStatus.all),
    client: APIKeyClient = Depends(get_client),
):
    try:
        return await client.list_project_keys(project_id, status=status)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/keys", response_model=APIKeyCreated, status_code=201)
async def create_key(body: CreateKeyBody, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.create_key(
            body.org_id,
            project_id=body.project_id,
            product_id=body.product_id,
            metadata=KeyMetadata(
                name=body.name,
                scopes=body.scopes,
                rate_limit=body.rate_limit,
                expires_at=body.expires_at,
                custom=body.custom,
            ),
        )
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/api/keys/{key_id}", response_model=APIKey)
async def update_key(key_id: str, body: UpdateKeyBody, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.update_key(
            key_id,
            metadata=KeyMetadata(
                name=body.name,
                scopes=body.scopes,
                rate_limit=body.rate_limit,
                expires_at=body.expires_at,
                custom=body.custom,
            ),
        )
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/keys/{key_id}/revoke", response_model=APIKey)
async def revoke_key(key_id: str, client: APIKeyClient = Depends(get_client)):
    """Soft-delete — disables the key but keeps the record for audit purposes."""
    try:
        return await client.revoke_key(key_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api/keys/{key_id}", status_code=204)
async def delete_key(key_id: str, client: APIKeyClient = Depends(get_client)):
    """Permanently erase the key record — use for GDPR erasure requests."""
    try:
        await client.delete_key(key_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/keys/verify", response_model=APIKey)
async def verify_key(body: VerifyKeyBody, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.verify_key(body.key)
    except ExpiredKeyError as e:
        detail = f"Key has expired"
        if e.expired_at:
            detail += f" at {e.expired_at.isoformat()}"
        raise HTTPException(status_code=401, detail=detail)
    except RevokedKeyError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidKeyError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except APIKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Example protected route using APIKeyDepends ───────────────────────────────

@router.get("/api/protected", response_model=dict)
async def protected_route(key: APIKey = Depends(require_read)):
    """Only accessible with a key that has the 'read' scope.
    APIKeyDepends handles header extraction and maps all exceptions to HTTP responses."""
    return {
        "key_id":      str(key.id),
        "scopes":      key.metadata.scopes,
        "use_count":   key.use_count,
        "last_used_at": str(key.last_used_at),
    }
