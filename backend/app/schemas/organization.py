from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_and_validate_cnpj(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("CNPJ must be a string")

    raw_cnpj = value.strip()
    if re.fullmatch(r"[0-9]{14}", raw_cnpj):
        cnpj = raw_cnpj
    elif re.fullmatch(r"[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}", raw_cnpj):
        cnpj = re.sub(r"[./-]", "", raw_cnpj)
    else:
        raise ValueError("CNPJ must contain 14 valid digits")

    if len(set(cnpj)) == 1:
        raise ValueError("CNPJ must contain 14 valid digits")

    digits = [int(digit) for digit in cnpj]
    first_weights = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    first_sum = sum(digit * weight for digit, weight in zip(digits[:12], first_weights))
    first_remainder = first_sum % 11
    first_check_digit = 0 if first_remainder < 2 else 11 - first_remainder

    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_sum = sum(
        digit * weight
        for digit, weight in zip(digits[:12] + [first_check_digit], second_weights)
    )
    second_remainder = second_sum % 11
    second_check_digit = 0 if second_remainder < 2 else 11 - second_remainder

    if digits[12:] != [first_check_digit, second_check_digit]:
        raise ValueError("CNPJ check digits are invalid")
    return cnpj


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    cnpj: str | None = Field(default=None, min_length=14, max_length=14)
    is_active: bool = True

    @field_validator("cnpj", mode="before")
    @classmethod
    def validate_cnpj(cls, value: str | None) -> str | None:
        return _normalize_and_validate_cnpj(value)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    cnpj: str | None = Field(default=None, min_length=14, max_length=14)
    
    is_active: bool = Field(default=None)

    @field_validator("cnpj", mode="before")
    @classmethod
    def validate_cnpj(cls, value: str | None) -> str | None:
        return _normalize_and_validate_cnpj(value)

    @field_validator("is_active", mode="before")
    @classmethod
    def is_active_cannot_be_null(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("is_active cannot be null")
        return value

    @field_validator("name")
    @classmethod
    def name_cannot_be_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        return value


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cnpj: str | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None
