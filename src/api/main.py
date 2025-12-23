"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware import (
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    TimingMiddleware,
)
from src.api.routes import api_router
from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router
from src.api.services import ConnectionManager
from src.core.config import Settings, get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager для FastAPI приложения.

    Выполняет инициализацию при старте и очистку при завершении.
    Инициализирует сервисы в app.state для Dependency Injection.
    """
    settings = get_settings()

    logger.info(
        "Starting AI Chat API server",
        extra={
            "version": settings.app_version,
            "environment": settings.app_env,
            "host": settings.api_host,
            "port": settings.api_port,
        },
    )

    # Инициализация сервисов в app.state
    app.state.settings = settings
    app.state.connection_manager = ConnectionManager()

    logger.info("Services initialized in app.state")

    # Предзагрузка конфигурации доменов (в thread pool чтобы не блокировать event loop)
    try:
        import asyncio

        from src.api.deps import load_domains_config

        # Выносим синхронное чтение файла в thread pool
        await asyncio.to_thread(load_domains_config)
        logger.info("Domains configuration loaded")
    except FileNotFoundError:
        logger.warning("Domains configuration file not found, using empty config")
    except Exception:
        logger.exception("Failed to load domains configuration")

    # Инициализация database engine и проверка подключения
    db_engine = None
    try:
        from src.db.engine import check_database_connection, get_engine

        db_engine = get_engine()
        is_connected = await check_database_connection(db_engine, timeout_seconds=10.0)
        if is_connected:
            logger.info("Database connection established")
            app.state.db_engine = db_engine
        else:
            logger.warning("Database connection failed, running in degraded mode")
    except Exception:
        logger.exception("Failed to initialize database")

    # Инициализация CheckpointerManager для LangGraph
    checkpointer_manager = None
    try:
        from src.graph.checkpointer import CheckpointerManager

        checkpointer_manager = CheckpointerManager()
        checkpointer = await checkpointer_manager.start()
        app.state.checkpointer_manager = checkpointer_manager
        app.state.checkpointer = checkpointer
        logger.info("LangGraph checkpointer initialized")
    except Exception:
        logger.exception("Failed to initialize LangGraph checkpointer")
        app.state.checkpointer = None

    # Инициализация ChatService с checkpointer
    try:
        from src.services.chat_service import ChatService

        chat_service = ChatService(checkpointer=app.state.checkpointer)
        app.state.chat_service = chat_service
        logger.info("ChatService initialized")
    except Exception:
        logger.exception("Failed to initialize ChatService")

    yield

    # Cleanup checkpointer
    if checkpointer_manager is not None:
        await checkpointer_manager.stop()
        logger.info("LangGraph checkpointer stopped")

    # Cleanup database engine
    if db_engine is not None:
        from src.db.engine import dispose_engine

        await dispose_engine(db_engine)
        logger.info("Database engine disposed")

    # Shutdown - очистка ресурсов
    logger.info(
        "Shutting down AI Chat API server",
        extra={
            "active_connections": app.state.connection_manager.active_count,
        },
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Создать и настроить FastAPI приложение.

    Args:
        settings: Настройки приложения. Если None, загружаются из env.

    Returns:
        Настроенное FastAPI приложение.
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="AI Chat API",
        description="Backend API для умного чат-ассистента с RAG и инструментами",
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Инициализируем сервисы в app.state (для тестов и синхронного доступа)
    # lifespan также вызовет эту инициализацию, но для TestClient это необходимо
    app.state.settings = settings
    app.state.connection_manager = ConnectionManager()
    app.state.checkpointer = None  # Будет инициализирован в lifespan
    app.state.chat_service = None  # Будет инициализирован в lifespan

    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Добавляем middleware (порядок важен - первый добавленный выполняется последним)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Регистрация роутеров
    app.include_router(health_router)  # /health, /health/ready, /health/live
    app.include_router(api_router)  # /api/v1/domains
    app.include_router(chat_router)  # /ws/chat/{thread_id}

    return app


# Создаём приложение для uvicorn
app = create_app()
