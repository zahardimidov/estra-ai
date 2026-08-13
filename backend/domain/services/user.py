from core.security import create_jwt_token, verify_password
from domain.entities import User
from infrastructure.db.uow import SqlAlchemyUnitOfWork


class UserService:
    def __init__(self, uow: SqlAlchemyUnitOfWork):
        self.uow = uow

    async def register(self, email: str, password: str) -> str:
        async with self.uow as uow:
            existing = await uow.users.find_one(email=email)
            if existing:
                raise ValueError("Email already exists")

            user = await uow.users.create(email=email, password=password)

        return create_jwt_token({"jwt_id": user.jwt_id})

    async def authenticate(self, email: str, password: str) -> str:
        async with self.uow as uow:
            user = await uow.users.find_one(email=email)

        if not user or not verify_password(password, user.password):
            raise ValueError("Invalid credentials")

        return create_jwt_token({"jwt_id": user.jwt_id})

    async def get_one_by_jwt_id(self, jwt_id: str):
        async with self.uow as uow:
            user = await uow.users.find_one(jwt_id=jwt_id)

        if user is None:
            return

        return User(id=user.id, email=user.email)
