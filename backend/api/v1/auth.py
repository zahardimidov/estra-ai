from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import CurrentUser, get_service
from api.v1.schemas.user import UserMe, UserSignIn, UserSignInResponse, UserSignUp
from domain.services import UserService

router = APIRouter(prefix="/auth", tags=['Auth'])


@router.post("/sign-up", response_model=UserSignInResponse, status_code=200)
async def signup(
    data: UserSignUp, service: UserService = Depends(get_service(UserService))
):
    try:
        token = await service.register(
            email=data.email, password=data.password
        )
    except ValueError:
        raise HTTPException(status_code=409, detail="Email already registered.")

    return {"token": token}


@router.post("/sign-in", response_model=UserSignInResponse, status_code=200)
async def signin(
    data: UserSignIn, service: UserService = Depends(get_service(UserService))
):
    try:
        token = await service.authenticate(email=data.email, password=data.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {"token": token}


@router.get("/me", response_model=UserMe, status_code=200)
async def me(user: CurrentUser):
    return user
