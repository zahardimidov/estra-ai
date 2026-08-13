from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from core.config import settings


def convert_datetime_to_iso_8601_with_z_suffix(dt: datetime) -> str:
    return dt.astimezone(settings.TIMEZONE).isoformat(timespec='seconds')


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(extra='forbid', json_encoders={
        datetime: convert_datetime_to_iso_8601_with_z_suffix
    })


class CustomStr(str):
    @classmethod
    def validate(cls, value):
        return value

    def __new__(cls, value):
        return cls.validate(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))
