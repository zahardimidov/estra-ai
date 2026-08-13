import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.security import hash_password


def generate_uuid():
    return str(uuid.uuid4())


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String, default=generate_uuid, primary_key=True, unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class AuthModel(Base):
    __abstract__ = True

    email = mapped_column(String(120), nullable=False, unique=True)
    _password = mapped_column("password", String(255), nullable=False)

    jwt_id = mapped_column(String, default=generate_uuid, unique=True, nullable=False)

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = hash_password(value)


class User(AuthModel):
    __tablename__ = "users"

    def __repr__(self):
        return f"{self.id} | {self.email}"


class ModerationTask(Base):
    __tablename__ = "moderation_tasks"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Exactly one of text_content/image_s3_path is set, depending on input_type
    input_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text | image
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_s3_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    callback_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    categories: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending | processing | completed | failed
    decision: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # approved | blocked

    # {category: probability}
    scores_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # {category: model_version} — which model version scored each category
    model_versions_used: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    @hybrid_property
    def completed_at(self):
        return self.updated_at

    def __repr__(self):
        return f"<ModerationTask {self.id} | {self.input_type} | {self.status}>"


class ApiKey(Base):
    __tablename__ = "api_keys"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Raw key is shown once on creation; only its SHA-256 hash is persisted
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    request_limit: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)

    def __repr__(self):
        return f"<ApiKey {self.id} | user={self.user_id} | {self.name}>"
