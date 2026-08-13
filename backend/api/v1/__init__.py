from fastapi import APIRouter
from fastapi.routing import APIRoute

from api.v1.apikeys import router as apikeys_router
from api.v1.auth import router as auth_router
from api.v1.moderation import router as moderation_router

router = APIRouter(prefix="/v1")


@router.get("/ping", status_code=200, include_in_schema=False)
def ping():
    return {"status": "ok"}


router.include_router(auth_router)
router.include_router(moderation_router)
router.include_router(apikeys_router)

for route in router.routes:
    if isinstance(route, APIRoute):
        route.response_model_exclude_none = True
        parts = route.name.split("_")
        route.operation_id = "".join(map(str.capitalize, parts))
