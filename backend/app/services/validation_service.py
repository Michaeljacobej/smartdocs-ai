from datetime import date

from app.schemas.extraction import ExtractedFields, ValidationAnomaly, ValidationResult

ALLOWED_CURRENCIES = {"IDR", "USD", "EUR", "SGD", "JPY", "MYR", "THB", "PHP"}


class ValidationService:
    def validate(self, data: ExtractedFields) -> ValidationResult:
        anomalies: list[ValidationAnomaly] = []

        if data.document_date is not None:
            try:
                date.fromisoformat(data.document_date)
            except ValueError:
                anomalies.append(
                    ValidationAnomaly(type="INVALID_DATE", message="Document date must be YYYY-MM-DD")
                )

        if data.currency is not None and data.currency not in ALLOWED_CURRENCIES:
            anomalies.append(
                ValidationAnomaly(type="INVALID_CURRENCY", message="Currency is not in allowed set")
            )

        if data.total_amount is not None and data.total_amount < 0:
            anomalies.append(
                ValidationAnomaly(type="INVALID_TOTAL", message="Total amount cannot be negative")
            )

        if data.tax_amount is not None and data.tax_amount < 0:
            anomalies.append(
                ValidationAnomaly(type="INVALID_TAX", message="Tax amount cannot be negative")
            )

        if (
            data.total_amount is not None
            and data.tax_amount is not None
            and data.tax_amount > data.total_amount
        ):
            anomalies.append(
                ValidationAnomaly(
                    type="TOTAL_TAX_INCONSISTENT",
                    message="Tax amount is greater than total amount",
                )
            )

        return ValidationResult(valid=len(anomalies) == 0, anomalies=anomalies)
