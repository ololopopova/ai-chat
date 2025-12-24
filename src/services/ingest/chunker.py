"""Chunker — разбиение документа на смысловые фрагменты.

Разбивает документ на чанки по заголовкам H1, сохраняя:
- Текст фрагмента
- Заголовок секции (в metadata)
- Порядковый номер
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.core.logging import get_logger
from src.services.ingest.html_parser import ParsedSection

logger = get_logger(__name__)


@dataclass
class ChunkResult:
    """
    Результат разбиения на чанки.

    Attributes:
        content: Текстовое содержимое чанка.
        chunk_index: Порядковый номер в документе (начиная с 0).
        metadata: Дополнительные метаданные (например, заголовок секции).
    """

    content: str
    chunk_index: int
    metadata: dict[str, Any]

    def to_dict(self, domain_id: UUID) -> dict[str, Any]:
        """
        Преобразовать в словарь для создания Chunk модели.

        Args:
            domain_id: UUID домена.

        Returns:
            Словарь с полями для ChunkRepository.create_batch().
        """
        return {
            "domain_id": domain_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "chunk_metadata": self.metadata,
        }


class Chunker:
    """
    Чанкер документов — разбиение на смысловые фрагменты.

    Стратегия:
    - Каждая секция с H1 заголовком = отдельный чанк
    - Заголовок сохраняется в metadata.header
    - Порядок чанков соответствует порядку секций
    """

    def __init__(self, min_chunk_size: int = 100) -> None:
        """
        Инициализация чанкера.

        Args:
            min_chunk_size: Минимальный размер чанка в символах.
                Чанки меньше этого размера будут пропущены (кроме случаев,
                когда секция явно задана).
        """
        self._min_chunk_size = min_chunk_size

    def chunk_sections(self, sections: list[ParsedSection]) -> list[ChunkResult]:
        """
        Разбить секции на чанки.

        Args:
            sections: Список распарсенных секций документа.

        Returns:
            Список чанков с порядковыми номерами.

        Note:
            Пустые секции пропускаются.
            Секции меньше min_chunk_size пропускаются (если это не единственная секция).
        """
        chunks: list[ChunkResult] = []
        chunk_index = 0

        for section in sections:
            # Пропустить пустые секции
            if not section.content or not section.content.strip():
                logger.debug(
                    "Skipping empty section",
                    extra={"header": section.header},
                )
                continue

            # Проверить минимальный размер (кроме случаев, когда это единственная секция)
            if len(section.content) < self._min_chunk_size and len(sections) > 1:
                logger.debug(
                    "Skipping too small section",
                    extra={
                        "header": section.header,
                        "size": len(section.content),
                        "min_size": self._min_chunk_size,
                    },
                )
                continue

            # Создать чанк
            chunk = ChunkResult(
                content=section.content,
                chunk_index=chunk_index,
                metadata={
                    "header": section.header,
                    "header_level": section.header_level,
                },
            )
            chunks.append(chunk)
            chunk_index += 1

        logger.info("Chunked document", extra={"chunks_count": len(chunks)})
        return chunks
