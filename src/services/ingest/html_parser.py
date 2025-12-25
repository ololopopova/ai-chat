"""HTML Parser — извлечение текста и таблиц из Google Docs HTML.

Парсит HTML экспорт Google Docs, извлекая:
- Заголовки (H1, H2, H3...)
- Текстовые параграфы
- Таблицы (конвертированные в структурированный текст)
"""

from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag  # type: ignore[attr-defined]

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedSection:
    """
    Распарсенная секция документа.

    Attributes:
        header: Заголовок секции (из H1/H2/H3 тега).
        header_level: Уровень заголовка (1-6).
        content: Текстовое содержимое секции.
    """

    header: str
    header_level: int
    content: str

    def __repr__(self) -> str:
        """Строковое представление."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ParsedSection(h{self.header_level}='{self.header}', content='{content_preview}')>"


class HTMLParser:
    """
    Парсер HTML экспорта Google Docs.

    Извлекает структурированный контент:
    - Разбивает по заголовкам H1
    - Извлекает текст между заголовками
    - Конвертирует таблицы в читаемый текст
    """

    def __init__(self) -> None:
        """Инициализация парсера."""
        pass

    def parse(self, html: str) -> list[ParsedSection]:
        """
        Распарсить HTML документа.

        Args:
            html: HTML контент (экспорт Google Docs).

        Returns:
            Список секций, разделённых по H1 заголовкам.

        Note:
            Если H1 заголовков нет, весь документ считается одной секцией.
        """
        soup = BeautifulSoup(html, "lxml")

        # Удалить скрипты и стили
        for script in soup(["script", "style"]):
            script.decompose()

        # Найти все H1 заголовки
        h1_tags = soup.find_all("h1")

        if not h1_tags:
            # Нет H1 — весь документ одна секция
            logger.debug("No H1 headers found, treating document as single section")
            body = soup.find("body") or soup
            content = self._extract_text(body)
            return [ParsedSection(header="Document", header_level=1, content=content)]

        sections: list[ParsedSection] = []

        for i, h1 in enumerate(h1_tags):
            header_text = h1.get_text(strip=True)

            # Найти все элементы между текущим H1 и следующим H1
            if i < len(h1_tags) - 1:
                next_h1 = h1_tags[i + 1]
                siblings = self._get_siblings_between(h1, next_h1)
            else:
                # Последняя секция — до конца документа
                siblings = list(h1.find_next_siblings())

            # Извлечь текст из элементов
            content_parts: list[str] = []
            for sibling in siblings:
                if isinstance(sibling, Tag):
                    text = self._extract_element_text(sibling)
                    if text:
                        content_parts.append(text)

            content = "\n\n".join(content_parts).strip()

            if content:  # Только непустые секции
                sections.append(ParsedSection(header=header_text, header_level=1, content=content))

        logger.info("Parsed document into sections", extra={"sections_count": len(sections)})
        return sections

    def _get_siblings_between(self, start: Tag, end: Tag) -> list[Tag | NavigableString]:
        """Получить все sibling элементы между start и end."""
        siblings: list[Tag | NavigableString] = []
        current = start.find_next_sibling()

        while current and current != end:
            siblings.append(current)
            current = current.find_next_sibling()

        return siblings

    def _extract_text(self, element: Tag) -> str:
        """
        Извлечь весь текст из элемента, включая таблицы.

        Args:
            element: BS4 Tag элемент.

        Returns:
            Текстовое представление.
        """
        parts: list[str] = []

        for child in element.descendants:
            if isinstance(child, Tag):
                if child.name == "table":
                    # Конвертировать таблицу в текст
                    table_text = self._parse_table(child)
                    if table_text:
                        parts.append(table_text)
                        # Пропустить descendants таблицы
                        for _ in child.descendants:
                            pass
                elif child.name in ["p", "div", "span"]:
                    text = child.get_text(strip=True)
                    if text and text not in parts:  # Избежать дубликатов
                        parts.append(text)

        return "\n\n".join(filter(None, parts)).strip()

    def _extract_element_text(self, element: Tag) -> str:
        """
        Извлечь текст из одного элемента.

        Args:
            element: BS4 Tag элемент.

        Returns:
            Текстовое представление.
        """
        if element.name == "table":
            return self._parse_table(element)
        elif element.name in [
            "p",
            "div",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
        ]:
            return element.get_text(separator="\n", strip=True)
        else:
            # Для остальных элементов — просто текст
            return element.get_text(strip=True)

    def _parse_table(self, table: Tag) -> str:
        """
        Конвертировать HTML таблицу в структурированный текст.

        Формат:
        Заголовок1: Значение1
        Заголовок2: Значение2
        ---
        Заголовок1: Значение1
        ...

        Args:
            table: BS4 Tag для таблицы.

        Returns:
            Текстовое представление таблицы.
        """
        rows = table.find_all("tr")
        if not rows:
            return ""

        # Первая строка как заголовки
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

        if not headers:
            return ""

        # Остальные строки как данные
        result_parts: list[str] = []

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            row_parts: list[str] = []
            for i, cell in enumerate(cells):
                value = cell.get_text(strip=True)
                if i < len(headers):
                    header = headers[i]
                    row_parts.append(f"{header}: {value}")
                else:
                    row_parts.append(value)

            if row_parts:
                result_parts.append("\n".join(row_parts))

        return "\n---\n".join(result_parts) if result_parts else ""
