# 🤖 AI Chat — Умный чат-ассистент

Демонстрационный проект умного чат-приложения с **ReAct Multi-Agent Architecture**, RAG и инструментами через MCP.

**Ключевые особенности:**
- 🧠 ReAct Main Agent с автономным принятием решений
- 🛠️ 3 специализированных субагента (products, compatibility, marketing)
- 🔄 Hot-reload для мгновенного применения изменений кода
- 📊 Стриминг событий в реальном времени
- 🗄️ PostgreSQL + pgvector для RAG
- 🐳 Полная dockerization с поддержкой разработки

## 🚀 Быстрый старт

### Требования

- Docker & Docker Compose

### Запуск (3 команды)

```bash
# 1. Настроить окружение
cp docker/env.docker.example docker/.env

# 2. (Опционально) Добавить API ключ для реальных ответов GPT
echo "OPENAI_API_KEY=sk-ваш-ключ" >> docker/.env

# 3. Запустить всё
docker compose -f docker/docker-compose.yml --profile app up -d --build
```

**Готово!**
- **UI:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

> **Без API ключа** система работает в mock-режиме — можно тестировать интерфейс.

### Применить миграции (первый запуск)

```bash
docker exec ai_chat_api alembic upgrade head
docker exec ai_chat_api python scripts/seed_domains.py
```

### 🔄 Hot-Reload для разработки

**Изменения применяются автоматически без перезапуска!**

✅ **Не требует перезапуска:**
- Любые изменения в `src/**/*.py` (Python код)
- Любые изменения в `ui/**/*.py` (Streamlit UI)
- Изменения в `config/*.yaml` (конфигурация)

⚠️ **Требует rebuild:**
- Изменения в `requirements.txt`
- Добавление новых миграций Alembic

```bash
# Только для изменений в requirements.txt
docker compose -f docker/docker-compose.yml --profile app up -d --build
```

---

<details>
<summary>🔧 Локальная разработка (без Docker для API)</summary>

Если хотите разрабатывать API локально:

```bash
# 1. Создать venv
python -m venv venv
source venv/bin/activate

# 2. Установить зависимости
pip install -r requirements-dev.txt

# 3. Запустить только БД
docker compose -f docker/docker-compose.yml up -d

# 4. Миграции
alembic upgrade head

# 5. Запустить API
python scripts/run_api.py

# 6. Запустить UI
streamlit run ui/app.py
```

</details>

## 📁 Структура проекта

```
ai-chat/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic configuration
│
├── config/                     # Конфигурационные файлы
│   ├── domains.yaml            # Конфигурация агентов (не доменов!)
│   └── llm.yaml                # Конфигурация LLM моделей
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
│   ├── graph/                  # LangGraph Orchestration (Phase 4)
│   │   ├── state.py            # ChatState (ReAct минималистичное)
│   │   ├── builder.py          # create_react_agent с tools
│   │   ├── prompts.py          # MAIN_AGENT_SYSTEM_PROMPT
│   │   ├── checkpointer.py     # PostgreSQL state persistence
│   │   └── tools/              # Субагенты как @tool функции
│   │       ├── products.py     # Products Agent (заглушка)
│   │       ├── compatibility.py # Compatibility Agent (заглушка)
│   │       └── marketing.py    # Marketing Agent (заглушка)
│   │
│   ├── llm/                    # LLM Provider (Phase 4)
│   │   ├── provider.py         # Unified LLM interface
│   │   ├── config.py           # LLM configuration
│   │   └── utils.py            # Response parsing
│   │
│   ├── services/               # Business Logic (Phase 4)
│   │   └── chat_service.py     # ChatService со стримингом
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

### Phase 4: ReAct Multi-Agent Architecture ✅

- ✅ **ReAct Main Agent** с автономным принятием решений
- ✅ **3 субагента как @tool функции:**
  - `products_agent` — БАДы, биохакинг, рецепты (заглушка)
  - `compatibility_agent` — сочетаемость продуктов (заглушка)
  - `marketing_agent` — генерация баннеров, анализ ЦА (заглушка)
- ✅ LLM Provider с поддержкой GPT-5.2 (reasoning_effort, output_verbosity)
- ✅ Конфигурация моделей через YAML (`config/llm.yaml`)
- ✅ Fallback модель (gpt-5.2 → gpt-5-mini)
- ✅ `create_react_agent` из LangGraph (вместо ручного графа)
- ✅ Минималистичный ChatState (messages + stage)
- ✅ MAIN_AGENT_SYSTEM_PROMPT с правилами работы
- ✅ AsyncPostgresSaver для персистентности состояния
- ✅ ChatService со стримингом событий (StageEvent, TokenEvent, ToolEvent)
- ✅ Mock режим при отсутствии API ключа
- ✅ Автоматические retry с exponential backoff (1s → 2s → 4s)
- ✅ Hot-reload для мгновенного применения изменений
- ✅ 120+ тестов (unit + integration)

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
{"type": "stage", "stage_name": "thinking", "message": "Анализирую запрос..."}
{"type": "stage", "stage_name": "calling_tool", "message": "Консультируюсь со специалистом..."}
{"type": "tool_start", "tool_name": "products_agent", "tool_input": {"query": "..."}}
{"type": "tool_end", "tool_name": "products_agent", "success": true, "result": "..."}
{"type": "token", "content": "Ч"}
{"type": "complete", "final_response": "...", "asset_url": null}
{"type": "error", "message": "...", "code": "GRAPH_ERROR", "timestamp": "..."}
{"type": "pong", "timestamp": "..."}
```

### Стадии обработки (ReAct)

| Stage | Описание |
|-------|----------|
| `thinking` | Main Agent анализирует запрос и планирует действия |
| `calling_tool` | Вызываются субагенты (products/compatibility/marketing) |
| `synthesizing` | Формируется финальный ответ на основе данных от tools |
| `complete` | Обработка завершена |

## 🧪 Тестирование

### Простые вопросы для ReAct агента

Попробуйте спросить:

| Вопрос | Какой субагент вызовется |
|--------|--------------------------|
| "Что принимать для сна?" | `products_agent` |
| "Какой БАД для сна и с чем его сочетать?" | `products_agent` + `compatibility_agent` |
| "Сделай баннер для акции на мелатонин" | `marketing_agent` |
| "Какая погода завтра?" | Off-topic (агент вежливо откажет) |

### Mock сценарии (без API ключа)

Для тестирования UI введите:

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

## 📋 Конфигурация

### Архитектурный принцип

Конфигурация разделена по назначению:

| Что | Где хранится | Почему |
|-----|--------------|--------|
| **Секреты** (API ключи) | `.env` / env vars | Не должны попадать в репозиторий |
| **Инфраструктура** (URLs, ports) | `.env` / env vars | Зависят от окружения |
| **Бизнес-логика** (модели LLM, параметры) | `config/*.yaml` | Читаемость + версионирование |

### LLM конфигурация (`config/llm.yaml`)

```yaml
models:
  default: "openai:gpt-5.2"      # Основная модель
  fallback: "openai:gpt-5-mini"  # Резервная при ошибках

generation:
  reasoning_effort: "low"   # none/low/medium/high/xhigh
  output_verbosity: "low"   # low/medium/high

infrastructure:
  timeout: 60
  max_retries: 3
  retry_delays: [1.0, 2.0, 4.0]
```

### Переменные окружения (`.env`)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| **Secrets (API Keys)** | | |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |
| **App** | | |
| `APP_ENV` | Окружение (development/staging/production) | development |
| `APP_DEBUG` | Режим отладки | false |
| **API Server** | | |
| `API_HOST` | Хост сервера | 0.0.0.0 |
| `API_PORT` | Порт сервера | 8000 |
| `API_RELOAD` | Hot reload (dev) | true |
| **Database** | | |
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://... |
| `DATABASE_POOL_SIZE` | Размер пула соединений | 5 |
| `DATABASE_ECHO` | SQL логирование | false |
| **Redis** | | |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| **API URLs** | | |
| `API_BASE_URL` | URL backend API | http://localhost:8000 |
| `API_WS_URL` | URL WebSocket | ws://localhost:8000 |
| **WebSocket** | | |
| `WS_HEARTBEAT_INTERVAL` | Интервал ping (сек) | 30 |
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

### ReAct Multi-Agent Flow

```
┌─────────────────────────────────────────────────────────┐
│                   MAIN AGENT (ReAct)                    │
│                                                         │
│  1. Думает: "Вопрос про БАДы и сочетаемость"          │
│  2. Действует:                                         │
│     → products_agent("Что для сна?")                   │
│     → compatibility_agent("Сочетаемость мелатонина")   │
│  3. Наблюдает: получает результаты                     │
│  4. Синтезирует: формирует единый ответ               │
└─────────────────────────────────────────────────────────┘
               ↓              ↓              ↓
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Products │   │Compat.   │   │Marketing │
        │  Agent   │   │  Agent   │   │  Agent   │
        │ (stub)   │   │ (stub)   │   │ (stub)   │
        └──────────┘   └──────────┘   └──────────┘
```

### Инфраструктура

```
┌─────────────┐     ┌─────────────────────────────────────────┐
│  Streamlit  │────▶│            FastAPI Backend              │
│     UI      │◀────│  (WebSocket + REST + Dependency Inj.)   │
└─────────────┘     └───────────────────┬─────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
              ┌─────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
              │Repository │      │  LangGraph  │     │    Tools    │
              │  Layer    │      │ ReAct Agent │     │  (MCP)      │
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

- [x] **Phase 1:** Streamlit UI + Mock
- [x] **Phase 2:** FastAPI Backend + WebSocket
- [x] **Phase 3:** Database Layer + Persistence
- [x] **Phase 4:** ReAct Multi-Agent Architecture ⭐ **(текущая)**
- [ ] **Phase 5:** RAG (Hybrid Retrieval) — индексация Google Docs
- [ ] **Phase 6:** Products Agent MCP — реальная база знаний
- [ ] **Phase 7:** Compatibility Agent MCP — база сочетаемости
- [ ] **Phase 8:** Marketing Agent MCP + Banner Generation Tool

### Текущий статус: Phase 4 Complete ✅

ReAct Main Agent работает с 3 субагентами-заглушками.  
Готов к интеграции реальных баз знаний через RAG (Phase 5).

## 📄 Лицензия

MIT
