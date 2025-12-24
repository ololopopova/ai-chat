"""Unit тесты для Chunker."""

from src.services.ingest.chunker import Chunker
from src.services.ingest.html_parser import ParsedSection


class TestChunker:
    """Тесты для Chunker."""

    def test_chunk_sections_basic(self) -> None:
        """Базовое разбиение на чанки."""
        sections = [
            ParsedSection(header="Секция 1", header_level=1, content="Контент секции 1" * 20),
            ParsedSection(header="Секция 2", header_level=1, content="Контент секции 2" * 20),
            ParsedSection(header="Секция 3", header_level=1, content="Контент секции 3" * 20),
        ]

        chunker = Chunker(min_chunk_size=100)
        chunks = chunker.chunk_sections(sections)

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[0].metadata["header"] == "Секция 1"
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2

    def test_chunk_sections_preserves_header(self) -> None:
        """Заголовок сохраняется в metadata."""
        sections = [
            ParsedSection(
                header="БАДы и добавки", header_level=1, content="Информация о БАДах" * 20
            ),
        ]

        chunker = Chunker(min_chunk_size=100)
        chunks = chunker.chunk_sections(sections)

        assert len(chunks) == 1
        assert chunks[0].metadata["header"] == "БАДы и добавки"
        assert chunks[0].metadata["header_level"] == 1

    def test_chunk_sections_skip_empty(self) -> None:
        """Пустые секции пропускаются."""
        sections = [
            ParsedSection(header="Секция 1", header_level=1, content="Контент" * 20),
            ParsedSection(header="Пустая", header_level=1, content=""),
            ParsedSection(header="Секция 2", header_level=1, content="Контент 2" * 20),
        ]

        chunker = Chunker(min_chunk_size=100)
        chunks = chunker.chunk_sections(sections)

        assert len(chunks) == 2
        assert chunks[0].metadata["header"] == "Секция 1"
        assert chunks[1].metadata["header"] == "Секция 2"

    def test_chunk_sections_skip_too_small(self) -> None:
        """Слишком маленькие секции пропускаются (если не единственная)."""
        sections = [
            ParsedSection(header="Большая", header_level=1, content="Контент" * 50),
            ParsedSection(header="Маленькая", header_level=1, content="Мало"),  # < 100 символов
            ParsedSection(header="Ещё большая", header_level=1, content="Текст" * 50),
        ]

        chunker = Chunker(min_chunk_size=100)
        chunks = chunker.chunk_sections(sections)

        assert len(chunks) == 2
        assert chunks[0].metadata["header"] == "Большая"
        assert chunks[1].metadata["header"] == "Ещё большая"

    def test_chunk_sections_single_small_section_included(self) -> None:
        """Если секция единственная, она включается даже если маленькая."""
        sections = [
            ParsedSection(header="Единственная", header_level=1, content="Мало текста"),
        ]

        chunker = Chunker(min_chunk_size=100)
        chunks = chunker.chunk_sections(sections)

        assert len(chunks) == 1
        assert chunks[0].metadata["header"] == "Единственная"

    def test_chunk_result_to_dict(self) -> None:
        """Преобразование ChunkResult в dict для БД."""
        from uuid import uuid4

        from src.services.ingest.chunker import ChunkResult

        domain_id = uuid4()
        chunk = ChunkResult(
            content="Тестовый контент",
            chunk_index=5,
            metadata={"header": "Тест", "header_level": 1},
        )

        chunk_dict = chunk.to_dict(domain_id)

        assert chunk_dict["domain_id"] == domain_id
        assert chunk_dict["content"] == "Тестовый контент"
        assert chunk_dict["chunk_index"] == 5
        assert chunk_dict["chunk_metadata"]["header"] == "Тест"

    def test_chunk_sections_preserves_order(self) -> None:
        """Порядок чанков соответствует порядку секций."""
        sections = [
            ParsedSection(header="Третья", header_level=1, content="3" * 100),
            ParsedSection(header="Первая", header_level=1, content="1" * 100),
            ParsedSection(header="Вторая", header_level=1, content="2" * 100),
        ]

        chunker = Chunker(min_chunk_size=100)
        chunks = chunker.chunk_sections(sections)

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[0].metadata["header"] == "Третья"
        assert chunks[1].chunk_index == 1
        assert chunks[1].metadata["header"] == "Первая"
        assert chunks[2].chunk_index == 2
        assert chunks[2].metadata["header"] == "Вторая"
