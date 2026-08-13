from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import CurrentUser, get_service
from api.v1.schemas.apikeys import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from domain.services.api_key import ApiKeyService

router = APIRouter(prefix="/apikeys", tags=["API Keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(
    data: ApiKeyCreateRequest,
    user: CurrentUser,
    service: ApiKeyService = Depends(get_service(ApiKeyService)),
):
    api_key, raw_key = await service.create_key(
        user_id=user.id,
        name=data.name,
        request_limit=data.request_limit,
    )
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        request_limit=api_key.request_limit,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[ApiKeyResponse], status_code=200)
async def list_api_keys(
    user: CurrentUser,
    service: ApiKeyService = Depends(get_service(ApiKeyService)),
):
    keys = await service.list_keys(user_id=user.id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            is_active=k.is_active,
            request_limit=k.request_limit,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    user: CurrentUser,
    service: ApiKeyService = Depends(get_service(ApiKeyService)),
):
    deleted = await service.delete_key(user_id=user.id, key_id=key_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
