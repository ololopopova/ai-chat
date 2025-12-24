"""Ingest Service — пайплайн загрузки и индексации документов.

Компоненты:
- GoogleDocLoader: Загрузка Google Docs
- HTMLParser: Парсинг HTML и извлечение контента
- Chunker: Разбиение текста на чанки
- EmbeddingService: Генерация embeddings
- IngestService: Оркестрация полного пайплайна
"""

from src.services.ingest.chunker import Chunker, ChunkResult
from src.services.ingest.embedding_service import EmbeddingService
from src.services.ingest.google_doc_loader import GoogleDocLoader
from src.services.ingest.html_parser import HTMLParser
from src.services.ingest.ingest_service import IngestResult, IngestService

__all__ = [
    "ChunkResult",
    "Chunker",
    "EmbeddingService",
    "GoogleDocLoader",
    "HTMLParser",
    "IngestResult",
    "IngestService",
]
