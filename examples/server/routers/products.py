from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apikeys import APIKeyClient, APIKeyError, Product
from apikeys.exceptions import AlreadyExistsError
from ..deps import get_client

router = APIRouter(tags=["products"])


class CreateProductBody(BaseModel):
    name: str


@router.get("/api/orgs/{org_id}/products", response_model=list[Product])
async def list_products(org_id: str, client: APIKeyClient = Depends(get_client)):
    try:
        await client.use_organization(org_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return await client.list_products(org_id)


@router.post("/api/orgs/{org_id}/products", response_model=Product, status_code=201)
async def create_product(
    org_id: str,
    body: CreateProductBody,
    client: APIKeyClient = Depends(get_client),
):
    try:
        return await client.create_product(org_id, body.name)
    except AlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/projects/{project_id}/products", response_model=list[Product])
async def list_project_products(project_id: str, client: APIKeyClient = Depends(get_client)):
    return await client.list_project_products(project_id)


@router.post("/api/products/{product_id}/projects/{project_id}", status_code=204)
async def link_product_to_project(
    product_id: str,
    project_id: str,
    client: APIKeyClient = Depends(get_client),
):
    try:
        await client.add_product_to_project(product_id, project_id)
    except APIKeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
