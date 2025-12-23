"""Middleware для FastAPI приложения."""

import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger

logger = get_logger(__name__)

# Context variable для хранения request_id
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Тип для call_next
RequestResponseEndpoint = Callable[[Request], Awaitable[Response]]


def get_request_id() -> str:
    """Получить текущий request_id из контекста."""
    return request_id_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления уникального request_id к каждому запросу."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Обработать запрос с добавлением request_id.

        Args:
            request: Входящий запрос
            call_next: Следующий обработчик в цепочке

        Returns:
            HTTP ответ с заголовком X-Request-ID
        """
        # Получаем или генерируем request_id
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        # Сохраняем в state для доступа в обработчиках
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования запросов."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Логировать входящие запросы и время выполнения.

        Args:
            request: Входящий запрос
            call_next: Следующий обработчик в цепочке

        Returns:
            HTTP ответ
        """
        # Пропускаем логирование для health check (чтобы не засорять логи)
        if request.url.path.startswith("/health"):
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "unknown")

        # Логируем начало запроса
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else "unknown",
            },
        )

        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Логируем завершение запроса
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return response

        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления заголовка X-Response-Time."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Добавить заголовок с временем выполнения запроса.

        Args:
            request: Входящий запрос
            call_next: Следующий обработчик в цепочке

        Returns:
            HTTP ответ с заголовком X-Response-Time
        """
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response

