import uuid
from dataclasses import dataclass, field
from datetime import datetime

from core.security import hash_api_key
from domain.services.api_key import ApiKeyService


@dataclass
class FakeUser:
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class FakeApiKey:
    user_id: str
    name: str
    key_hash: str
    is_active: bool = True
    request_limit: int = 1000
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)


class FakeApiKeyRepository:
    def __init__(self):
        self._storage: list[FakeApiKey] = []

    async def create(self, **data) -> FakeApiKey:
        row = FakeApiKey(**data)
        self._storage.append(row)
        return row

    async def find(self, **conditions) -> list[FakeApiKey]:
        return [r for r in self._storage if all(getattr(r, k, None) == v for k, v in conditions.items())]

    async def find_by_hash(self, key_hash: str) -> FakeApiKey | None:
        return next((r for r in self._storage if r.key_hash == key_hash and r.is_active), None)

    async def get(self, key_id: str) -> FakeApiKey | None:
        return next((r for r in self._storage if r.id == key_id), None)

    async def delete(self, key_id: str) -> None:
        self._storage = [r for r in self._storage if r.id != key_id]


class FakeUserRepository:
    def __init__(self):
        self._storage: list[FakeUser] = []

    async def get(self, user_id: str) -> FakeUser | None:
        return next((u for u in self._storage if u.id == user_id), None)


class FakeUoW:
    def __init__(self, users: FakeUserRepository | None = None):
        self.api_keys = FakeApiKeyRepository()
        self.users = users or FakeUserRepository()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# --- create_key ---

async def test_create_key_returns_entity_and_raw_key():
    service = ApiKeyService(FakeUoW())

    entity, raw_key = await service.create_key(user_id="u1", name="prod")

    assert entity.name == "prod"
    assert entity.user_id == "u1"
    assert raw_key.startswith("sk-")


async def test_create_key_stores_hash_not_raw_key():
    uow = FakeUoW()
    service = ApiKeyService(uow)

    _, raw_key = await service.create_key(user_id="u1", name="prod")

    stored = uow.api_keys._storage[0]
    assert stored.key_hash == hash_api_key(raw_key)
    assert stored.key_hash != raw_key


async def test_create_key_uses_custom_request_limit():
    service = ApiKeyService(FakeUoW())

    entity, _ = await service.create_key(user_id="u1", name="prod", request_limit=50)

    assert entity.request_limit == 50


# --- list_keys ---

async def test_list_keys_returns_only_owned_keys():
    uow = FakeUoW()
    service = ApiKeyService(uow)
    await service.create_key(user_id="u1", name="key-a")
    await service.create_key(user_id="u2", name="key-b")

    keys = await service.list_keys(user_id="u1")

    assert len(keys) == 1
    assert keys[0].name == "key-a"


async def test_list_keys_empty_when_none_created():
    service = ApiKeyService(FakeUoW())

    keys = await service.list_keys(user_id="u1")

    assert keys == []


# --- delete_key ---

async def test_delete_key_removes_own_key():
    uow = FakeUoW()
    service = ApiKeyService(uow)
    entity, _ = await service.create_key(user_id="u1", name="prod")

    deleted = await service.delete_key(user_id="u1", key_id=entity.id)

    assert deleted is True
    assert await uow.api_keys.get(entity.id) is None


async def test_delete_key_rejects_other_users_key():
    uow = FakeUoW()
    service = ApiKeyService(uow)
    entity, _ = await service.create_key(user_id="u1", name="prod")

    deleted = await service.delete_key(user_id="u2", key_id=entity.id)

    assert deleted is False
    assert await uow.api_keys.get(entity.id) is not None


async def test_delete_key_unknown_id_returns_false():
    service = ApiKeyService(FakeUoW())

    deleted = await service.delete_key(user_id="u1", key_id="nonexistent-id")

    assert deleted is False


# --- get_user_by_raw_key ---

async def test_get_user_by_raw_key_returns_owning_user():
    users = FakeUserRepository()
    owner = FakeUser(email="owner@example.com")
    users._storage.append(owner)
    uow = FakeUoW(users=users)
    service = ApiKeyService(uow)
    _, raw_key = await service.create_key(user_id=owner.id, name="prod")

    user = await service.get_user_by_raw_key(raw_key)

    assert user is not None
    assert user.id == owner.id
    assert user.email == owner.email


async def test_get_user_by_raw_key_unknown_key_returns_none():
    service = ApiKeyService(FakeUoW())

    user = await service.get_user_by_raw_key("sk-does-not-exist")

    assert user is None


# --- get_key_by_raw_key ---

async def test_get_key_by_raw_key_returns_key_entity():
    uow = FakeUoW()
    service = ApiKeyService(uow)
    created, raw_key = await service.create_key(user_id="u1", name="prod", request_limit=50)

    api_key = await service.get_key_by_raw_key(raw_key)

    assert api_key is not None
    assert api_key.id == created.id
    assert api_key.request_limit == 50


async def test_get_key_by_raw_key_unknown_key_returns_none():
    service = ApiKeyService(FakeUoW())

    api_key = await service.get_key_by_raw_key("sk-does-not-exist")

    assert api_key is None
