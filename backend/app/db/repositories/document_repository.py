from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)
        return document

    def list(self) -> list[Document]:
        stmt = (
            select(Document)
            .options(
                joinedload(Document.ocr_result),
                joinedload(Document.extracted_data),
                joinedload(Document.summary),
            )
            .order_by(Document.upload_date.desc())
        )
        return list(self.db.scalars(stmt).unique())

    def get(self, document_id: UUID) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                joinedload(Document.ocr_result),
                joinedload(Document.extracted_data),
                joinedload(Document.summary),
            )
        )
        return self.db.scalars(stmt).unique().first()

    def delete(self, document: Document) -> None:
        self.db.delete(document)
