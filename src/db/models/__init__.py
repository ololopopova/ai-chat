"""SQLAlchemy ORM модели для AI Chat.

Модели:
- Domain: Домены знаний (тематические области)
- Chunk: Фрагменты знаний для RAG
- Conversation: История диалогов
- Job: Фоновые задачи
"""

from src.db.models.chunk import Chunk
from src.db.models.conversation import Conversation
from src.db.models.domain import Domain
from src.db.models.job import Job, JobStatus

__all__ = [
    "Chunk",
    "Conversation",
    "Domain",
    "Job",
    "JobStatus",
]
