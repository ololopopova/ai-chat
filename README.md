# 🤖 AI Chat — Умный чат-ассистент

Демонстрационный проект умного чат-приложения с RAG, агентной оркестрацией и инструментами через MCP.

## 🚀 Быстрый старт

### Требования

- Python 3.12+
- Docker & Docker Compose (для PostgreSQL и Redis)
- pip

### Установка

1. **Клонировать репозиторий:**
```bash
git clone <repository-url>
cd ai-chat
```

2. **Создать виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows
```

3. **Установить зависимости:**
```bash
# Для разработки (включает ruff, mypy, pytest)
pip install -r requirements-dev.txt

# Только для запуска
pip install -r requirements.txt
```

4. **Настроить переменные окружения:**
```bash
cp .env.example .env
# Отредактировать .env при необходимости
```

5. **Запустить инфраструктуру (PostgreSQL + Redis):**
```bash
# Настроить переменные Docker
cp docker/env.docker.example docker/.env

# Запустить контейнеры
docker compose -f docker/docker-compose.yml up -d

# Проверить статус
docker compose -f docker/docker-compose.yml ps
```

6. **Инициализировать базу данных:**
```bash
# Применить миграции
python scripts/init_db.py

# Заполнить домены
python scripts/seed_domains.py
```

### Запуск приложения

**1. Запустить FastAPI backend:**
```bash
python scripts/run_api.py
```
Backend будет доступен по адресу: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**2. В отдельном терминале запустить Streamlit UI:**
```bash
streamlit run ui/app.py
```
UI будет доступен по адресу: http://localhost:8501

> **Note:** По умолчанию UI работает в mock-режиме. Для подключения к backend отключите "Mock API" в боковой панели или установите `USE_MOCK_API=false` в `.env`.

### 🐳 Запуск через Docker (полный стек)

```bash
# Запустить всё (PostgreSQL, Redis, API, UI)
docker compose -f docker/docker-compose.yml --profile app up -d

# Применить миграции
docker exec ai_chat_api python scripts/init_db.py
docker exec ai_chat_api python scripts/seed_domains.py

# Проверить логи
docker compose -f docker/docker-compose.yml logs -f api
```

Приложение будет доступно:
- **UI:** http://localhost:8501
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## 📁 Структура проекта

```
ai-chat/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic configuration
│
├── config/                     # Конфигурационные файлы
│   └── domains.yaml            # Конфигурация доменов
│
├── docker/                     # Docker configuration
│   ├── docker-compose.yml      # PostgreSQL, Redis, API, UI
│   ├── Dockerfile.api          # API image
│   ├── Dockerfile.ui           # UI image
│   └── postgres/init.sql       # PostgreSQL extensions
│
├── src/                        # Backend
│   ├── core/                   # Ядро приложения
│   │   ├── config.py           # Pydantic Settings
│   │   ├── exceptions.py       # Базовые и Repository исключения
│   │   └── logging.py          # Настройка логирования
│   │
│   ├── db/                     # Database Layer (Phase 3)
│   │   ├── base.py             # Base ORM model + TimestampMixin
│   │   ├── engine.py           # Async SQLAlchemy engine
│   │   ├── session.py          # AsyncSession factory
│   │   └── models/             # ORM models
│   │       ├── domain.py       # Domain (knowledge areas)
│   │       ├── chunk.py        # Chunk (RAG fragments)
│   │       ├── conversation.py # Conversation (chat history)
│   │       └── job.py          # Job (async tasks)
│   │
│   ├── repositories/           # Repository Pattern (Phase 3)
│   │   ├── base.py             # Generic CRUD + batch operations
│   │   ├── protocols.py        # Repository interfaces (DIP)
│   │   ├── unit_of_work.py     # Unit of Work pattern
│   │   ├── domain_repository.py
│   │   ├── chunk_repository.py # FTS + Vector search
│   │   ├── conversation_repository.py
│   │   └── job_repository.py
│   │
│   └── api/                    # FastAPI backend
│       ├── main.py             # App factory + lifespan
│       ├── deps.py             # Dependency injection
│       ├── middleware.py       # Request ID, Logging, Timing
│       ├── routes/             # Endpoints
│       │   ├── health.py       # /health (DB + Redis checks)
│       │   ├── domains.py      # /api/v1/domains
│       │   └── chat.py         # /ws/chat/{thread_id}
│       ├── schemas/            # Pydantic schemas
│       └── services/           # Business logic
│
├── ui/                         # Streamlit UI
│   ├── app.py                  # Точка входа
│   ├── session.py              # Менеджер сессии
│   ├── api_client.py           # WebSocket API клиент
│   ├── components/             # UI компоненты
│   ├── models/                 # Pydantic модели событий
│   └── mock/                   # Mock клиент
│
├── scripts/                    # CLI скрипты
│   ├── run_api.py              # Запуск FastAPI сервера
│   ├── init_db.py              # Инициализация БД
│   └── seed_domains.py         # Заполнение доменов
│
└── tests/                      # Тесты
    ├── unit/                   # Unit тесты
    └── integration/            # Integration тесты (DB, API)
```

## 🎯 Функциональность

### Phase 1: Streamlit UI ✅

- ✅ История сообщений (user/assistant)
- ✅ Стриминг ответа (эффект печатания)
- ✅ Timeline стадий обработки
- ✅ Прогресс-бар для долгих операций
- ✅ Отображение изображений
- ✅ Множественные диалоги с переключением
- ✅ Mock API для демонстрации

### Phase 2: FastAPI Backend + WebSocket ✅

- ✅ FastAPI сервер с CORS, middleware
- ✅ WebSocket endpoint `/ws/chat/{thread_id}`
- ✅ REST endpoints: `/health`, `/api/v1/domains`
- ✅ Стриминг событий в реальном времени
- ✅ Echo-режим для демонстрации
- ✅ Dependency Injection через `app.state`
- ✅ Reconnect логика в клиенте

### Phase 3: Database Layer + Persistence ✅

- ✅ PostgreSQL 16 + pgvector + pg_trgm
- ✅ Redis 7 для кэширования и очередей
- ✅ SQLAlchemy 2.0 async (asyncpg)
- ✅ Alembic миграции
- ✅ Repository Pattern с Generic CRUD
- ✅ Unit of Work для транзакций
- ✅ Protocol interfaces (SOLID DIP)
- ✅ FTS + Vector search для RAG
- ✅ Health checks с реальной проверкой зависимостей
- ✅ 100+ тестов (unit + integration)

## 🌐 API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/health` | GET | Health check (DB + Redis + LLM status) |
| `/health/ready` | GET | Kubernetes readiness probe |
| `/health/live` | GET | Kubernetes liveness probe |
| `/api/v1/domains` | GET | Список доступных доменов |
| `/ws/chat/{thread_id}` | WS | WebSocket для чата |
| `/docs` | GET | Swagger UI (только dev) |

### WebSocket протокол

**Client → Server:**
```json
{"type": "message", "content": "Текст сообщения", "metadata": {}}
{"type": "ping"}
```

**Server → Client:**
```json
{"type": "stage", "stage_name": "router", "message": "Анализирую запрос..."}
{"type": "token", "content": "Ч"}
{"type": "complete", "final_response": "...", "asset_url": null}
{"type": "error", "message": "...", "code": "INVALID_MESSAGE", "timestamp": "..."}
{"type": "pong", "timestamp": "..."}
```

## 🧪 Mock сценарии

Для тестирования введите:

| Ключевые слова | Сценарий |
|----------------|----------|
| `баннер`, `картинка` | Генерация баннера с прогрессом |
| `ошибка`, `сломай` | Имитация ошибки |
| `погода`, `анекдот` | Off-topic ответ |
| Любой другой текст | RAG ответ |

## 🛠 Разработка

### Проверка качества кода

```bash
# Линтинг
ruff check .

# Форматирование
ruff format .

# Проверка типов
mypy src scripts
```

### Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Только unit тесты
pytest tests/unit/ -v

# Только integration тесты (требует PostgreSQL)
pytest tests/integration/ -v

# С покрытием
pytest tests/ --cov=src --cov=ui
```

### Работа с миграциями

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "add new table"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Показать историю
alembic history
```

### Управление Docker

```bash
# Запустить только инфраструктуру (DB + Redis)
docker compose -f docker/docker-compose.yml up -d

# Запустить полный стек (+ API + UI)
docker compose -f docker/docker-compose.yml --profile app up -d

# Остановить
docker compose -f docker/docker-compose.yml down

# Удалить с данными
docker compose -f docker/docker-compose.yml down -v

# Пересобрать образы
docker compose -f docker/docker-compose.yml --profile app up -d --build
```

## 📋 Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| **App** | | |
| `APP_ENV` | Окружение (development/staging/production) | development |
| `APP_DEBUG` | Режим отладки | false |
| `APP_VERSION` | Версия приложения | 0.1.0 |
| **API Server** | | |
| `API_HOST` | Хост сервера | 0.0.0.0 |
| `API_PORT` | Порт сервера | 8000 |
| `API_RELOAD` | Hot reload (dev) | true |
| **Database** | | |
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://... |
| `DATABASE_POOL_SIZE` | Размер пула соединений | 5 |
| `DATABASE_MAX_OVERFLOW` | Доп. соединения | 10 |
| `DATABASE_ECHO` | SQL логирование | false |
| **Redis** | | |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| **API URLs** | | |
| `API_BASE_URL` | URL backend API | http://localhost:8000 |
| `API_WS_URL` | URL WebSocket | ws://localhost:8000 |
| **CORS** | | |
| `CORS_ORIGINS` | Разрешённые origins | ["http://localhost:8501"] |
| **WebSocket** | | |
| `WS_HEARTBEAT_INTERVAL` | Интервал ping (сек) | 30 |
| `WS_MESSAGE_MAX_SIZE` | Макс. размер сообщения | 65536 |
| `WS_CONNECTION_TIMEOUT` | Таймаут соединения (сек) | 300 |
| **UI** | | |
| `UI_TITLE` | Заголовок страницы | AI Ассистент |
| `USE_MOCK_API` | Использовать mock API | true |

## 📦 Стек технологий

### Backend
- **Python** 3.12+
- **FastAPI** — Backend API + WebSocket
- **Uvicorn** — ASGI сервер
- **SQLAlchemy** 2.0 — Async ORM
- **asyncpg** — PostgreSQL async driver
- **Alembic** — Database migrations
- **Pydantic** — валидация данных
- **redis-py** — Redis async client

### Database
- **PostgreSQL** 16 — основная БД
- **pgvector** — векторный поиск
- **pg_trgm** — fuzzy text search
- **Redis** 7 — кэш и очереди

### Frontend
- **Streamlit** — UI framework
- **websockets** — WebSocket клиент
- **httpx** — HTTP клиент

### DevOps
- **Docker** + **Docker Compose**
- **ruff** — линтинг и форматирование
- **mypy** — проверка типов
- **pytest** — тестирование

## 🏗 Архитектура

```
┌─────────────┐     ┌─────────────────────────────────────────┐
│  Streamlit  │────▶│            FastAPI Backend              │
│     UI      │◀────│  (WebSocket + REST + Dependency Inj.)   │
└─────────────┘     └───────────────────┬─────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
              ┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
              │Repository │      │  LangGraph  │     │    MCP      │
              │  Layer    │      │ (orchestr.) │     │  (tools)    │
              └─────┬─────┘      └─────────────┘     └─────────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
    ┌────▼────┐ ┌───▼───┐ ┌────▼────┐
    │PostgreSQL│ │ Redis │ │pgvector │
    │ (data)  │ │(cache)│ │ (RAG)   │
    └─────────┘ └───────┘ └─────────┘
```

## 🗺 Roadmap

- [x] Phase 1: Streamlit UI + Mock
- [x] Phase 2: FastAPI Backend + WebSocket
- [x] Phase 3: Database Layer + Persistence
- [ ] Phase 4: LLM Integration (OpenAI)
- [ ] Phase 5: RAG (Hybrid Retrieval)
- [ ] Phase 6: LangGraph Orchestration
- [ ] Phase 7: MCP Tools Integration

## 📄 Лицензия

MIT
