# 🤖 AI Chat — Умный чат-ассистент

Демонстрационный (портфолио) проект умного чат-приложения с **ReAct Multi-Agent Architecture**, **RAG Subagents** через MCP и расширяемой экосистемой инструментов.

**Ключевые особенности:**
- 🧠 **ReAct Main Agent** с автономным принятием решений
- 🤖 **3 специализированных RAG субагента** (products, compatibility, marketing)
- 🔍 **Hybrid Search** (Vector + FTS) с Cross-Encoder Reranker
- 🔧 **MCP Protocol** для расширяемых инструментов
- 📊 **Стриминг событий** в реальном времени
- 🔄 **Hot-reload** для мгновенного применения изменений кода
- 🗄️ **PostgreSQL + pgvector** для RAG
- 🐳 **Полная dockerization** с поддержкой разработки

## 🚀 Быстрый старт

### Требования

- Docker & Docker Compose
- (Опционально) OpenAI API ключ для реальных ответов

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
- **Adminer (DB UI):** http://localhost:8080
- **Dozzle (Logs UI):** http://localhost:9999

> **Без API ключа** система работает в mock-режиме — можно тестировать интерфейс.

### Применить миграции и загрузить данные (первый запуск)

```bash
# Миграции БД
docker exec ai_chat_api alembic upgrade head

# Загрузить тестовые домены
docker exec ai_chat_api python scripts/seed_domains.py

# Индексация базы знаний (если есть Google Docs)
# docker exec ai_chat_api python scripts/ingest.py
```

### 🔄 Hot-Reload для разработки

**Изменения применяются автоматически без перезапуска!**

✅ **Не требует перезапуска:**
- Любые изменения в `src/**/*.py` (Python код)
- Любые изменения в `mcp_servers/**/*.py` (MCP серверы)
- Любые изменения в `ui/**/*.py` (Streamlit UI)
- Изменения в `config/*.yaml` (конфигурация)

⚠️ **Требует rebuild:**
- Изменения в `requirements.txt`
- Добавление новых миграций Alembic

```bash
# Для rebuild после изменений в requirements.txt
docker compose -f docker/docker-compose.yml build --no-cache api
docker compose -f docker/docker-compose.yml up -d
```

### 🐛 Просмотр логов

**Dozzle (Web UI):**
```bash
# Запустить Dozzle (если не запущен)
docker compose -f docker/docker-compose.yml --profile debug up -d

# Открыть http://localhost:9999
```

**Терминал:**
```bash
# Все сервисы
docker compose -f docker/docker-compose.yml logs -f

# Только API
docker compose -f docker/docker-compose.yml logs -f api

# Только UI
docker compose -f docker/docker-compose.yml logs -f ui
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
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Запустить только БД и Redis
docker compose -f docker/docker-compose.yml up -d postgres redis

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
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration scripts
│   └── env.py                     # Alembic configuration
│
├── config/                        # Конфигурационные файлы
│   ├── domains.yaml               # Конфигурация субагентов и RAG
│   └── llm.yaml                   # Конфигурация LLM моделей
│
├── docker/                        # Docker infrastructure
│   ├── docker-compose.yml         # PostgreSQL, Redis, API, UI, Adminer, Dozzle
│   ├── Dockerfile.api             # API image (с предзагрузкой Reranker)
│   ├── Dockerfile.ui              # UI image
│   ├── env.docker.example         # Пример .env
│   └── postgres/init.sql          # PostgreSQL extensions (pgvector, pg_trgm)
│
├── mcp_servers/                   # MCP Servers (расширяемые инструменты)
│   └── rag/                       # RAG MCP Server
│       ├── server.py              # FastMCP server
│       ├── tools.py               # hybrid_search tool
│       ├── search.py              # Multi-query hybrid search logic
│       ├── reranker.py            # Cross-Encoder reranker
│       └── schemas.py             # Pydantic schemas
│
├── src/                           # Backend
│   ├── core/                      # Ядро приложения
│   │   ├── config.py              # Pydantic Settings
│   │   ├── exceptions.py          # Базовые и Repository исключения
│   │   └── logging.py             # Structured JSON logging
│   │
│   ├── db/                        # Database Layer
│   │   ├── base.py                # Base ORM model + TimestampMixin
│   │   ├── engine.py              # Async SQLAlchemy engine
│   │   ├── session.py             # AsyncSession factory
│   │   └── models/                # ORM models
│   │       ├── domain.py          # Domain (knowledge areas)
│   │       ├── chunk.py           # Chunk (RAG fragments, FTS + Vector)
│   │       ├── conversation.py    # Conversation (chat history)
│   │       └── job.py             # Job (async tasks)
│   │
│   ├── repositories/              # Repository Pattern (Data Access Layer)
│   │   ├── base.py                # Generic CRUD + batch operations
│   │   ├── protocols.py           # Repository interfaces (SOLID DIP)
│   │   ├── unit_of_work.py        # Unit of Work pattern
│   │   ├── domain_repository.py
│   │   ├── chunk_repository.py    # Hybrid search (FTS + Vector)
│   │   ├── conversation_repository.py
│   │   └── job_repository.py
│   │
│   ├── graph/                     # LangGraph Orchestration
│   │   ├── state.py               # ChatState (messages + stage)
│   │   ├── builder.py             # build_chat_graph (ReAct Main Agent)
│   │   ├── checkpointer.py        # AsyncPostgresSaver wrapper
│   │   ├── prompts/               # System prompts (модульная структура)
│   │   │   ├── main_agent.py      # Main Agent prompt
│   │   │   ├── products_subagent.py
│   │   │   ├── compatibility_subagent.py
│   │   │   └── marketing_subagent.py
│   │   └── subagents/             # RAG Subagents (ReAct graphs)
│   │       ├── base.py            # SubagentConfig, create_rag_subagent
│   │       ├── products.py        # Products субагент (RAG + MCP tools)
│   │       ├── compatibility.py   # Compatibility субагент (RAG + MCP tools)
│   │       └── marketing.py       # Marketing субагент (placeholder)
│   │
│   ├── llm/                       # LLM Provider Abstraction
│   │   ├── provider.py            # Unified LLM interface
│   │   ├── config.py              # LLM configuration
│   │   └── utils.py               # Response parsing
│   │
│   ├── services/                  # Business Logic Layer
│   │   ├── chat_service.py        # ChatService со стримингом событий
│   │   └── ingest/                # Индексация базы знаний
│   │       ├── google_docs_loader.py
│   │       ├── chunker.py
│   │       └── embedding_service.py
│   │
│   └── api/                       # FastAPI backend
│       ├── main.py                # App factory + lifespan (с предзагрузкой Reranker)
│       ├── deps.py                # Dependency injection
│       ├── middleware.py          # Request ID, Logging, Timing
│       ├── routes/                # Endpoints
│       │   ├── health.py          # /health (DB + Redis checks)
│       │   ├── domains.py         # /api/v1/domains
│       │   └── chat.py            # /ws/chat/{thread_id}
│       ├── schemas/               # Pydantic schemas
│       └── services/              # API services
│           └── connection_manager.py
│
├── ui/                            # Streamlit UI
│   ├── app.py                     # Точка входа
│   ├── session.py                 # Менеджер сессии
│   ├── api_client.py              # WebSocket API клиент
│   ├── components/                # UI компоненты
│   ├── models/                    # Pydantic модели событий
│   └── mock/                      # Mock клиент
│
├── scripts/                       # CLI скрипты
│   ├── run_api.py                 # Запуск FastAPI сервера
│   ├── init_db.py                 # Инициализация БД
│   ├── seed_domains.py            # Заполнение доменов
│   └── ingest.py                  # Индексация базы знаний
│
└── tests/                         # Тесты
    ├── unit/                      # Unit тесты (graph, RAG, subagents)
    └── integration/               # Integration тесты (DB, API, WebSocket)
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
- ✅ Dependency Injection через `app.state`
- ✅ Reconnect логика в клиенте
- ✅ Structured JSON logging

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

### Phase 4: ReAct Multi-Agent Architecture ✅

- ✅ **ReAct Main Agent** с автономным принятием решений
- ✅ **3 субагента как @tool функции:**
  - `products_agent` — БАДы, биохакинг, рецепты
  - `compatibility_agent` — сочетаемость продуктов
  - `marketing_agent` — генерация баннеров, анализ ЦА (placeholder)
- ✅ LLM Provider с поддержкой GPT-5.2 (reasoning_effort, output_verbosity)
- ✅ Конфигурация моделей через YAML (`config/llm.yaml`)
- ✅ Fallback модель (gpt-5.2 → gpt-5-mini)
- ✅ `create_react_agent` из LangGraph
- ✅ Минималистичный ChatState (messages + stage)
- ✅ Модульные system prompts (`src/graph/prompts/`)
- ✅ AsyncPostgresSaver для персистентности состояния
- ✅ ChatService со стримингом событий
- ✅ Mock режим при отсутствии API ключа
- ✅ Автоматические retry с exponential backoff
- ✅ Hot-reload для мгновенного применения изменений

### Phase 5: RAG (Hybrid Retrieval) ✅

- ✅ Google Docs loader через публичные ссылки
- ✅ Semantic chunking (SmartChunker)
- ✅ OpenAI Embeddings (text-embedding-3-large)
- ✅ PostgreSQL Full-Text Search (tsvector, ts_rank)
- ✅ pgvector Vector Search (cosine similarity)
- ✅ Hybrid search (dense + sparse merge)
- ✅ Индексация через CLI скрипт (`scripts/ingest.py`)

### Phase 6: Subagents with RAG (Subgraph Architecture) ✅ **(текущая)**

- ✅ **RAG MCP Server** с `hybrid_search` tool
  - Multi-query parallel search (vector + FTS)
  - Deduplication (max score per chunk)
  - Cross-Encoder Reranker (ms-marco-MiniLM-L-12-v2)
  - Фильтрация по `min_score`
- ✅ **Products Subagent** (ReAct граф + RAG MCP tools)
  - Доступ к истории через `InjectedState`
  - Собственный LLM для query planning
  - Генерация `vector_queries` и `fts_keywords`
- ✅ **Compatibility Subagent** (ReAct граф + RAG MCP tools)
- ✅ **Marketing Subagent** (placeholder)
- ✅ **Production-Ready Reranker:**
  - Модель кэшируется в Docker образ (~50MB)
  - Предзагружается при старте API (если `use_reranker=true`)
  - Singleton для переиспользования (не загружается при каждом запросе)
- ✅ Конфигурация через `config/domains.yaml` (субагенты, RAG параметры)
- ✅ Unit + Integration тесты

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

### Примеры вопросов для ReAct агента

Попробуйте спросить:

| Вопрос | Какой субагент вызовется |
|--------|--------------------------|
| "Что принимать для сна?" | `products_agent` (с RAG поиском) |
| "Какой БАД для сна и с чем его сочетать?" | `products_agent` + `compatibility_agent` |
| "Совместимость магния и кальция" | `compatibility_agent` |
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

# Запустить с debug tools (+ Dozzle для логов)
docker compose -f docker/docker-compose.yml --profile app --profile debug up -d

# Остановить
docker compose -f docker/docker-compose.yml down

# Удалить с данными
docker compose -f docker/docker-compose.yml down -v

# Пересобрать образы (после изменений в requirements.txt или Dockerfile)
docker compose -f docker/docker-compose.yml build --no-cache api
docker compose -f docker/docker-compose.yml up -d

# Очистить __pycache__ (если hot-reload не работает)
find . -type d -name "__pycache__" -exec rm -rf {} +
docker compose -f docker/docker-compose.yml restart api ui
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

### RAG конфигурация (`config/domains.yaml`)

```yaml
subagents:
  llm_model: "openai:gpt-5-mini"  # Модель для субагентов
  history_window: 6               # История диалога (последние N сообщений)

  products:
    domain: "products"            # Домен для RAG поиска
    rag_min_score: 0.3            # Минимальный порог релевантности

  compatibility:
    domain: "compatibility"
    rag_min_score: 0.3

rag:
  dense_weight: 0.7               # Вес векторного поиска
  sparse_weight: 0.3              # Вес полнотекстового поиска
  top_k_per_query: 5              # Результатов на подзапрос
  final_top_k: 15                 # Итоговое количество
  use_reranker: true              # Включить Cross-Encoder reranking
```

### Переменные окружения (`.env`)

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| **Secrets (API Keys)** | | |
| `OPENAI_API_KEY` | OpenAI API key | - |
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
| **WebSocket** | | |
| `WS_HEARTBEAT_INTERVAL` | Интервал ping (сек) | 30 |
| `WS_CONNECTION_TIMEOUT` | Таймаут соединения (сек) | 300 |
| **UI** | | |
| `UI_TITLE` | Заголовок страницы | AI Ассистент |
| `USE_MOCK_API` | Использовать mock API | false |
| **Debug Tools** | | |
| `DOZZLE_PORT` | Порт Dozzle (logs UI) | 9999 |

## 📦 Стек технологий

### Backend
- **Python** 3.13
- **FastAPI** — Backend API + WebSocket
- **Uvicorn** — ASGI сервер
- **SQLAlchemy** 2.0 — Async ORM
- **asyncpg** — PostgreSQL async driver
- **Alembic** — Database migrations
- **Pydantic** — валидация данных
- **redis-py** — Redis async client

### AI/ML
- **LangChain** — LLM abstractions
- **LangGraph** — Agent orchestration
- **OpenAI** — GPT models
- **sentence-transformers** — Cross-Encoder reranker
- **MCP (Model Context Protocol)** — расширяемые инструменты

### Database
- **PostgreSQL** 16 — основная БД
- **pgvector** — векторный поиск (cosine similarity)
- **pg_trgm** — Full-Text Search (FTS) с морфологией
- **Redis** 7 — кэш и очереди

### Frontend
- **Streamlit** — UI framework
- **websockets** — WebSocket клиент
- **httpx** — HTTP клиент

### DevOps
- **Docker** + **Docker Compose**
- **Dozzle** — Web UI для логов
- **Adminer** — Web UI для PostgreSQL
- **ruff** — линтинг и форматирование
- **mypy** — проверка типов
- **pytest** — тестирование

## 🏗 Архитектура

### ReAct Multi-Agent Flow с RAG

```
┌─────────────────────────────────────────────────────────────┐
│                   MAIN AGENT (ReAct)                        │
│                                                             │
│  1. Думает: "Вопрос про БАДы и сочетаемость"              │
│  2. Действует:                                             │
│     → products_agent("Что для сна?")                       │
│     → compatibility_agent("Сочетаемость мелатонина")       │
│  3. Наблюдает: получает результаты от субагентов           │
│  4. Синтезирует: формирует единый ответ                    │
└─────────────────────────────────────────────────────────────┘
               ↓              ↓              ↓
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Products │   │Compat.   │   │Marketing │
        │ Subagent │   │ Subagent │   │ Subagent │
        │ (ReAct)  │   │ (ReAct)  │   │(placeholder)
        └─────┬────┘   └─────┬────┘   └──────────┘
              │              │
              ↓              ↓
        ┌──────────────────────────┐
        │   RAG MCP Server         │
        │  - hybrid_search tool    │
        │  - Multi-query           │
        │  - Deduplication         │
        │  - Cross-Encoder Reranker│
        └─────────┬────────────────┘
                  ↓
        ┌──────────────────────────┐
        │  PostgreSQL + pgvector   │
        │  - Full-Text Search      │
        │  - Vector Search         │
        │  - Hybrid Merge          │
        └──────────────────────────┘
```

### RAG Hybrid Search Pipeline

```
User Query → Subagent LLM (Query Planning)
                    ↓
          ┌─────────────────────┐
          │ vector_queries (3)  │ → Semantic search
          │ fts_keywords (7)    │ → Keyword search
          └─────────────────────┘
                    ↓
            Parallel Search (10 queries)
                    ↓
          ┌─────────────────────┐
          │ Vector: 15 chunks   │
          │ FTS:    35 chunks   │
          └─────────────────────┘
                    ↓
          Deduplication (max score)
                    ↓
          Cross-Encoder Reranker
                    ↓
          Filter by min_score (0.3)
                    ↓
          Top-15 chunks → Context
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
              │Repository │      │  LangGraph  │     │  MCP Tools  │
              │  Layer    │      │ ReAct Agent │     │  (RAG)      │
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
- [x] **Phase 4:** ReAct Multi-Agent Architecture
- [x] **Phase 5:** RAG (Hybrid Retrieval) — индексация Google Docs
- [x] **Phase 6:** Subagents with RAG (Subgraph Architecture) ⭐ **(текущая)**
- [ ] **Phase 7:** Banner Generation Tool (MCP) + Marketing Agent
- [ ] **Phase 8:** Production Deployment (CI/CD, Monitoring)

### Текущий статус: Phase 6 Complete ✅

**ReAct Main Agent** работает с 3 RAG субагентами:
- **Products Subagent** — полноценный ReAct граф с RAG MCP tools
- **Compatibility Subagent** — полноценный ReAct граф с RAG MCP tools
- **Marketing Subagent** — placeholder для будущих инструментов

**Готово к интеграции новых инструментов через MCP!**

## 🎓 Демонстрация компетенций

Этот проект демонстрирует:

### 1. Современная архитектура AI систем
- ✅ **ReAct Agents** — автономное принятие решений
- ✅ **Multi-Agent Architecture** — специализация и масштабируемость
- ✅ **RAG (Retrieval Augmented Generation)** — гибридный поиск
- ✅ **MCP Protocol** — расширяемость инструментов

### 2. Профессиональная инженерия
- ✅ **Clean Architecture** — слои, SOLID, DIP
- ✅ **Repository Pattern + Unit of Work** — чистый Data Access Layer
- ✅ **Dependency Injection** — через `app.state` и Protocol interfaces
- ✅ **Production-Ready оптимизации** — синглтоны, кэширование моделей
- ✅ **Structured Logging** — JSON логи для парсинга и анализа

### 3. Качество кода
- ✅ **Type Safety** — mypy, Pydantic, type hints
- ✅ **Code Style** — ruff (линтинг + форматирование)
- ✅ **Тесты** — unit + integration (pytest)
- ✅ **Миграции** — Alembic для версионирования БД

### 4. DevOps/Infrastructure
- ✅ **Docker/Docker Compose** — полная контейнеризация
- ✅ **Hot-Reload** — быстрая итерация при разработке
- ✅ **Health Checks** — Kubernetes-ready probes
- ✅ **Debug Tools** — Dozzle (logs), Adminer (DB)
- ✅ **Environment Management** — .env + YAML конфиги

### 5. Масштабируемость
- ✅ **Async/Await** — асинхронность на всех уровнях
- ✅ **PostgreSQL Pool** — эффективное использование соединений
- ✅ **Redis** — готовность к кэшированию и очередям
- ✅ **Модульная структура** — легко добавлять новые субагенты

## 📄 Лицензия

MIT
