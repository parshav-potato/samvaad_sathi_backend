import datetime

import pydantic

from src.models.schemas.base import BaseSchemaModel


class UserCreate(BaseSchemaModel):
    email: pydantic.EmailStr
    password: str
    name: str


class UserLogin(BaseSchemaModel):
    email: pydantic.EmailStr
    password: str


class UserWithToken(BaseSchemaModel):
    token: str
    email: pydantic.EmailStr
    name: str
    created_at: datetime.datetime


class UserInResponse(BaseSchemaModel):
    id: int
    authorized_user: UserWithToken


