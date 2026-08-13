import uuid
from dataclasses import dataclass, field

import pytest

from core.security import hash_password
from domain.services.user import UserService


@dataclass
class FakeUser:
    email: str
    password: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    jwt_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class FakeUserRepository:
    def __init__(self):
        self._storage: list[FakeUser] = []

    async def find_one(self, **conditions) -> FakeUser | None:
        for user in self._storage:
            if all(getattr(user, k, None) == v for k, v in conditions.items()):
                return user
        return None

    async def create(self, email: str, password: str, **_) -> FakeUser:
        user = FakeUser(email=email, password=hash_password(password))
        self._storage.append(user)
        return user


class FakeUoW:
    def __init__(self):
        self.users = FakeUserRepository()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# --- register ---

async def test_register_returns_token():
    service = UserService(FakeUoW())

    token = await service.register(email="user@example.com", password="secret")

    assert isinstance(token, str) and len(token) > 0


async def test_register_duplicate_email_raises():
    uow = FakeUoW()
    service = UserService(uow)

    await service.register(email="user@example.com", password="secret")

    with pytest.raises(ValueError, match="Email already exists"):
        await service.register(email="user@example.com", password="other")


# --- authenticate ---

async def test_authenticate_returns_token():
    uow = FakeUoW()
    service = UserService(uow)
    await service.register(email="user@example.com", password="secret")

    token = await service.authenticate(email="user@example.com", password="secret")

    assert isinstance(token, str) and len(token) > 0


async def test_authenticate_wrong_password_raises():
    uow = FakeUoW()
    service = UserService(uow)
    await service.register(email="user@example.com", password="secret")

    with pytest.raises(ValueError, match="Invalid credentials"):
        await service.authenticate(email="user@example.com", password="wrong")


async def test_authenticate_unknown_email_raises():
    service = UserService(FakeUoW())

    with pytest.raises(ValueError, match="Invalid credentials"):
        await service.authenticate(email="ghost@example.com", password="secret")
