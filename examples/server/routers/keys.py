from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apikeys import APIKey, APIKeyClient, APIKeyCreated, APIKeyError, InsufficientScopeError, InvalidKeyError, RevokedKeyError
from ..deps import get_client

router = APIRouter(tags=["keys"])


class CreateKeyBody(BaseModel):
    org_id: str
    project_id: Optional[str] = None
    product_id: Optional[str] = None
    name: Optional[str] = None
    scopes: list[str] = []
    rate_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    custom: dict = {}


class VerifyKeyBody(BaseModel):
    key: str


@router.get("/api/orgs/{org_id}/keys", response_model=list[APIKey])
async def list_org_keys(org_id: str, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.list_org_keys(org_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/projects/{project_id}/keys", response_model=list[APIKey])
async def list_keys(project_id: str, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.list_project_keys(project_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/keys", response_model=APIKeyCreated, status_code=201)
async def create_key(body: CreateKeyBody, client: APIKeyClient = Depends(get_client)):
    from apikeys import KeyMetadata
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


@router.delete("/api/keys/{key_id}", response_model=APIKey)
async def revoke_key(key_id: str, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.revoke_key(key_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/keys/verify", response_model=APIKey)
async def verify_key(body: VerifyKeyBody, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.verify_key(body.key)
    except RevokedKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except APIKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
