CLASSIFICATION_RULE_HINT = """
Classify this transaction document into exactly one of the following labels:
- invoice
- receipt
- billing_statement
- other

Rules:
- Use invoice if the document is a customer invoice, commercial bill, or billing document with line items and a total amount.
- Use receipt if the document is a payment proof, transaction receipt, or proof of purchase.
- Use billing_statement if the document is a statement, account summary, or periodic billing document.
- Use other for anything that does not match the categories above.

Important:
- Return only one lowercase label.
- Do not return explanatory text, punctuation, or a sentence.
- Use the exact label names above, including billing_statement with underscore.
- If the document is ambiguous, prefer the label that best matches the main purpose of the document.
"""
