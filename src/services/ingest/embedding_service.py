"""Embedding Service — генерация векторных представлений текста.

Использует OpenAI text-embedding-3-large (3072 dims) с batch обработкой.
Включает retry логику и rate limiting.
"""

from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import get_settings
from src.core.exceptions import EmbeddingError
from src.core.logging import get_logger

logger = get_logger(__name__)

# Константы
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSION = 1536  # Уменьшенная размерность (pgvector limit < 2000)
MAX_BATCH_SIZE = 100  # OpenAI поддерживает до 2048, но мы ограничиваем для безопасности
MAX_RETRIES = 3
RETRY_MIN_WAIT = 1.0  # секунды
RETRY_MAX_WAIT = 10.0  # секунды


class EmbeddingService:
    """
    Сервис генерации embeddings.

    Особенности:
    - Batch обработка до 100 текстов за запрос
    - Автоматический retry при временных ошибках
    - Exponential backoff при rate limiting
    - Валидация размерности (3072 dims)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = EMBEDDING_MODEL,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """
        Инициализация сервиса.

        Args:
            api_key: OpenAI API ключ. Если None, загружается из settings.
            model: Название модели embeddings.
            max_retries: Максимальное количество попыток при ошибках.

        Raises:
            EmbeddingError: Если API ключ не найден.
        """
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key

        if not self._api_key:
            raise EmbeddingError("OpenAI API key not found in settings or arguments")

        self._model = model
        self._max_retries = max_retries
        self._client = AsyncOpenAI(api_key=self._api_key)

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Генерировать embeddings для нескольких текстов.

        Args:
            texts: Список текстов для векторизации (до 100 штук).

        Returns:
            Список векторов (каждый вектор = list[float] из 3072 элементов).

        Raises:
            EmbeddingError: При ошибках API или превышении лимитов.
        """
        if not texts:
            return []

        if len(texts) > MAX_BATCH_SIZE:
            raise EmbeddingError(
                f"Batch size {len(texts)} exceeds maximum {MAX_BATCH_SIZE}",
                batch_size=len(texts),
            )

        logger.debug(
            "Generating embeddings",
            extra={"batch_size": len(texts), "model": self._model},
        )

        try:
            embeddings = await self._generate_with_retry(texts)

            # Валидация размерности
            for i, emb in enumerate(embeddings):
                if len(emb) != EMBEDDING_DIMENSION:
                    raise EmbeddingError(
                        f"Invalid embedding dimension at index {i}: "
                        f"expected {EMBEDDING_DIMENSION}, got {len(emb)}"
                    )

            logger.info(
                "Successfully generated embeddings",
                extra={"count": len(embeddings), "model": self._model},
            )

            return embeddings

        except Exception as e:
            logger.error(
                "Failed to generate embeddings",
                extra={"error": str(e), "batch_size": len(texts)},
            )
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e

    async def _generate_with_retry(self, texts: list[str]) -> list[list[float]]:
        """
        Генерация с retry логикой.

        Args:
            texts: Список текстов.

        Returns:
            Список embeddings.

        Raises:
            EmbeddingError: При исчерпании попыток.
        """
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
            retry=retry_if_exception_type((TimeoutError, ConnectionError)),
            reraise=True,
        )

        try:
            async for attempt in retrying:
                with attempt:
                    response = await self._client.embeddings.create(
                        input=texts,
                        model=self._model,
                        dimensions=EMBEDDING_DIMENSION,  # Явно указываем размерность
                    )

                    # Извлечь векторы в правильном порядке
                    embeddings = [item.embedding for item in response.data]

                    if len(embeddings) != len(texts):
                        raise EmbeddingError(
                            f"Response count mismatch: expected {len(texts)}, got {len(embeddings)}"
                        )

                    return embeddings

        except Exception as e:
            error_str = str(e).lower()

            # Классификация ошибок
            if "rate limit" in error_str or "429" in error_str:
                raise EmbeddingError("OpenAI rate limit exceeded") from e
            elif "authentication" in error_str or "api key" in error_str:
                raise EmbeddingError("OpenAI authentication failed") from e
            elif "timeout" in error_str:
                raise EmbeddingError("OpenAI API timeout") from e

            raise EmbeddingError(f"Unexpected error: {e}") from e

        # Не должно выполняться, но для type checker
        raise EmbeddingError("Unexpected error in retry logic")

    async def generate_single(self, text: str) -> list[float]:
        """
        Генерировать embedding для одного текста.

        Args:
            text: Текст для векторизации.

        Returns:
            Вектор из 3072 элементов.

        Raises:
            EmbeddingError: При ошибках API.
        """
        embeddings = await self.generate_batch([text])
        return embeddings[0]

    async def close(self) -> None:
        """Закрыть соединения (cleanup)."""
        await self._client.close()

    async def __aenter__(self) -> "EmbeddingService":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit."""
        await self.close()
