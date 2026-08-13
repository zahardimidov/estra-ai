import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from core.config import settings
from core.logging import get_logger

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
logger = get_logger(__name__)

ALGORITHM = "HS256"
EXPIRE = timedelta(hours=settings.JWT_TOKEN_LIFETIME)


def create_jwt_token(data: dict, expire=EXPIRE) -> str:
    expiration = datetime.now(timezone.utc) + expire
    payload = {**data, "exp": expiration}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_jwt_token(token: str) -> dict | None:
    try:
        decoded_data = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )
        return decoded_data
    except jwt.PyJWTError:
        logger.debug("Invalid JWT token", exc_info=True)
        return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str | bytes, hash: str | bytes) -> bool:
    return pwd_context.verify(password, hash)


def generate_api_key() -> str:
    """Generate a random API key in the format sk-<64 hex chars>."""
    return f"sk-{secrets.token_hex(32)}"


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key (fast, suitable for DB lookup)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()
