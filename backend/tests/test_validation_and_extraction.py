import pytest
from pydantic import ValidationError

from app.schemas.extraction import ExtractedFields


def test_extraction_schema_validation_invalid_date() -> None:
    with pytest.raises(ValidationError):
        ExtractedFields(document_date="09-30-2026")
