EXTRACTION_PROMPT_TEMPLATE = """
You are extracting structured transaction data from OCR text.

Use ONLY information explicitly present in the OCR text.
Never invent or infer unsupported values.
If a field cannot be found, return null.
Return valid JSON only.
Normalize dates to YYYY-MM-DD.
Return monetary amounts as numbers without currency symbols.
Preserve the vendor name as written in the document.

Expected JSON:
{{
  "document_number": string | null,
  "vendor": string | null,
  "document_date": string | null,
  "total": number | null,
  "tax_amount": number | null,
  "currency": string | null
}}

OCR TEXT:
{ocr_text}
"""
