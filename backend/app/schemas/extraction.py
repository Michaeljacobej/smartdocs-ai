from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils.amount_parser import parse_amount


class ExtractedFields(BaseModel):
    document_number: str | None = None
    vendor: str | None = None
    document_date: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    currency: str | None = None

    @field_validator("document_date")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        date.fromisoformat(value)
        return value

    @field_validator("total_amount", "tax_amount", mode="before")
    @classmethod
    def normalize_amount(cls, value: str | float | int | None) -> float | None:
        return parse_amount(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class CorrectionInput(BaseModel):
    document_number: str | None = None
    vendor: str | None = None
    document_date: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    currency: str | None = None

    model_config = ConfigDict(extra="forbid")


class ValidationAnomaly(BaseModel):
    type: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    anomalies: list[ValidationAnomaly] = []
