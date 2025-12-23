"""Repository layer для AI Chat.

Репозитории реализуют паттерн Repository для доступа к данным.
Каждый репозиторий инкапсулирует логику работы с конкретной моделью.

Patterns:
    - Repository Pattern: инкапсуляция доступа к данным
    - Unit of Work: группировка операций в транзакции
    - Protocol/Interface: контракты для DIP compliance
"""

from src.repositories.base import BaseRepository
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.job_repository import JobRepository
from src.repositories.protocols import (
    ChunkRepositoryProtocol,
    ConversationRepositoryProtocol,
    DomainRepositoryProtocol,
    JobRepositoryProtocol,
    RepositoryProtocol,
)
from src.repositories.unit_of_work import UnitOfWork, get_unit_of_work

__all__ = [
    "BaseRepository",
    "ChunkRepository",
    "ChunkRepositoryProtocol",
    "ConversationRepository",
    "ConversationRepositoryProtocol",
    "DomainRepository",
    "DomainRepositoryProtocol",
    "JobRepository",
    "JobRepositoryProtocol",
    "RepositoryProtocol",
    "UnitOfWork",
    "get_unit_of_work",
]
