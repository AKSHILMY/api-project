from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apikeys import APIKeyClient, APIKeyError, Project
from apikeys.exceptions import AlreadyExistsError
from ..deps import get_client

router = APIRouter(tags=["projects"])


class CreateProjectBody(BaseModel):
    name: str


@router.get("/api/orgs/{org_id}/projects", response_model=list[Project])
async def list_projects(org_id: str, client: APIKeyClient = Depends(get_client)):
    try:
        await client.use_organization(org_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return await client.list_projects(org_id)


@router.post("/api/orgs/{org_id}/projects", response_model=Project, status_code=201)
async def create_project(
    org_id: str,
    body: CreateProjectBody,
    client: APIKeyClient = Depends(get_client),
):
    try:
        return await client.create_project(org_id, body.name)
    except AlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
