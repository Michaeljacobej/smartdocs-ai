from app.services.document_service import document_service
from app.services.llm.ollama import OllamaProvider
from app.services.summary_service import SummaryService

summary_service = SummaryService(llm_provider=OllamaProvider())

__all__ = ["document_service", "summary_service"]
