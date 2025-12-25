"""Google Docs Loader — загрузка публичных Google документов.

Извлекает DOC_ID из URL и загружает HTML через публичный export API.
"""

import re

import httpx

from src.core.exceptions import IngestError
from src.core.logging import get_logger

logger = get_logger(__name__)

# Таймауты (секунды)
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 60.0  # Увеличен для больших документов


class GoogleDocLoader:
    """
    Загрузчик публичных Google документов.

    Поддерживает различные форматы URL:
    - https://docs.google.com/document/d/{DOC_ID}/edit
    - https://docs.google.com/document/d/{DOC_ID}/edit?tab=t.0
    - https://docs.google.com/document/d/{DOC_ID}
    """

    # Паттерн для извлечения DOC_ID
    DOC_ID_PATTERN = re.compile(
        r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",
        re.IGNORECASE,
    )

    # Шаблон для экспорта
    EXPORT_TEMPLATE = "https://docs.google.com/document/d/{doc_id}/export?format=html"

    def __init__(
        self, timeout: tuple[float, float] = (CONNECT_TIMEOUT, READ_TIMEOUT)
    ) -> None:
        """
        Инициализация загрузчика.

        Args:
            timeout: Кортеж (connect_timeout, read_timeout) в секундах.
        """
        self._timeout = timeout

    def extract_doc_id(self, url: str) -> str:
        """
        Извлечь DOC_ID из URL Google Doc.

        Args:
            url: Полный URL документа.

        Returns:
            DOC_ID (например, "1AbC123xyz").

        Raises:
            IngestError: Если URL невалидный или DOC_ID не найден.

        Examples:
            >>> loader = GoogleDocLoader()
            >>> loader.extract_doc_id(
            ...     "https://docs.google.com/document/d/ABC123/edit"
            ... )
            'ABC123'
        """
        match = self.DOC_ID_PATTERN.search(url)
        if not match:
            raise IngestError(f"Invalid Google Doc URL: {url}")

        doc_id = match.group(1)
        logger.debug("Extracted DOC_ID from URL", extra={"doc_id": doc_id, "url": url})
        return doc_id

    async def load(self, url: str) -> str:
        """
        Загрузить HTML документа.

        Args:
            url: URL Google документа (любой поддерживаемый формат).

        Returns:
            HTML контент документа.

        Raises:
            IngestError: При ошибках загрузки (404, 403, timeout и т.д.)
        """
        doc_id = self.extract_doc_id(url)
        export_url = self.EXPORT_TEMPLATE.format(doc_id=doc_id)

        logger.info(
            "Loading Google Doc", extra={"doc_id": doc_id, "export_url": export_url}
        )

        try:
            timeout = httpx.Timeout(
                connect=self._timeout[0],
                read=self._timeout[1],
                write=self._timeout[1],
                pool=self._timeout[0],
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(export_url, follow_redirects=True)

                # Проверка статуса
                if response.status_code == 404:
                    raise IngestError(f"Document not found: {doc_id}")
                elif response.status_code == 403:
                    raise IngestError(f"Document is not public: {doc_id}")
                elif response.status_code != 200:
                    raise IngestError(
                        f"Failed to load document: {doc_id}, status={response.status_code}"
                    )

                html = response.text
                logger.info(
                    "Successfully loaded Google Doc",
                    extra={"doc_id": doc_id, "size_bytes": len(html)},
                )

                return html

        except httpx.TimeoutException as e:
            logger.error("Timeout loading Google Doc", extra={"doc_id": doc_id})
            raise IngestError(f"Timeout loading document: {doc_id}") from e
        except httpx.HTTPError as e:
            logger.error(
                "HTTP error loading Google Doc",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            raise IngestError(f"HTTP error loading document: {doc_id}") from e
        except Exception as e:
            logger.error(
                "Unexpected error loading Google Doc",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            raise IngestError(f"Unexpected error loading document: {doc_id}") from e

    def build_export_url(self, url: str) -> str:
        """
        Построить export URL из обычного URL документа.

        Args:
            url: URL Google документа.

        Returns:
            Export URL для загрузки HTML.

        Raises:
            IngestError: Если URL невалидный.
        """
        doc_id = self.extract_doc_id(url)
        return self.EXPORT_TEMPLATE.format(doc_id=doc_id)
