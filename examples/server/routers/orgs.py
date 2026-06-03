from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apikeys import APIKeyClient, APIKeyError, Organization
from apikeys.exceptions import AlreadyExistsError
from ..deps import get_client

router = APIRouter(prefix="/api/orgs", tags=["organizations"])


class CreateOrgBody(BaseModel):
    name: str


@router.get("", response_model=list[Organization])
async def list_orgs(client: APIKeyClient = Depends(get_client)):
    return await client.list_organizations()


@router.post("", response_model=Organization, status_code=201)
async def create_org(body: CreateOrgBody, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.create_organization(body.name)
    except AlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{org_id}", response_model=Organization)
async def get_org(org_id: str, client: APIKeyClient = Depends(get_client)):
    try:
        return await client.use_organization(org_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
