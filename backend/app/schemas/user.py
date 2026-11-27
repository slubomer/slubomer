"""Login and user management requests and responses."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import ApiModel

# Long passwords beat complex rules; the upper limit stops absurd inputs.
Password = Annotated[str, Field(min_length=12, max_length=128)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    totp_code: str | None = Field(default=None, max_length=10, description="Kód z aplikácie 2FA")


class UserOut(ApiModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool
    totp_enabled: bool
    last_login_at: datetime | None


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str  # frontend shows it as a QR code


class TotpConfirmRequest(BaseModel):
    code: str = Field(max_length=10)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: Password


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    role: UserRole
    password: Password


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: UserRole | None = None
    is_active: bool | None = None
    password: Password | None = None
