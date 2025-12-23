# 🤖 AI Chat — Умный чат-ассистент

Демонстрационный проект умного чат-приложения с RAG, агентной оркестрацией и инструментами через MCP.

## 🚀 Быстрый старт

### Требования

- Python 3.12+
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

## 📁 Структура проекта

```
ai-chat/
├── config/                     # Конфигурационные файлы
│   └── domains.yaml           # Конфигурация доменов
│
├── src/                        # Backend
│   ├── core/                  # Ядро приложения
│   │   ├── config.py          # Pydantic Settings
│   │   ├── exceptions.py      # Базовые исключения
│   │   └── logging.py         # Настройка логирования
│   │
│   └── api/                   # FastAPI backend (Phase 2)
│       ├── main.py            # App factory
│       ├── deps.py            # Dependency injection
│       ├── middleware.py      # Request ID, Logging, Timing
│       ├── routes/            # Endpoints
│       │   ├── health.py      # /health, /health/ready, /health/live
│       │   ├── domains.py     # /api/v1/domains
│       │   └── chat.py        # /ws/chat/{thread_id}
│       ├── schemas/           # Pydantic schemas
│       └── services/          # Business logic
│           ├── connection_manager.py
│           └── message_handler.py
│
├── ui/                         # Streamlit UI
│   ├── app.py                 # Точка входа
│   ├── session.py             # Менеджер сессии
│   ├── api_client.py          # WebSocket API клиент
│   ├── components/            # UI компоненты
│   ├── models/                # Pydantic модели событий
│   └── mock/                  # Mock клиент
│
├── scripts/                    # CLI скрипты
│   └── run_api.py             # Запуск FastAPI сервера
│
└── tests/                      # Тесты
    ├── unit/                  # Unit тесты
    └── integration/           # Integration тесты
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
- ✅ Echo-режим для демонстрации (временно, будет заменён на LLM)
- ✅ Dependency Injection через `app.state`
- ✅ Reconnect логика в клиенте
- ✅ 80 тестов (unit + integration)

## 🌐 API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/health` | GET | Health check с версией и зависимостями |
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

# Только integration тесты
pytest tests/integration/ -v

# С покрытием
pytest tests/ --cov=src --cov=ui
```

**Покрытие:** 80 тестов (unit + integration)

### Запуск API сервера

```bash
# С настройками по умолчанию
python scripts/run_api.py

# С параметрами
python scripts/run_api.py --host 127.0.0.1 --port 8080 --no-reload

# Опции
python scripts/run_api.py --help
```

## 📋 Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `APP_ENV` | Окружение (development/staging/production) | development |
| `APP_DEBUG` | Режим отладки | false |
| `APP_VERSION` | Версия приложения | 0.1.0 |
| **API Server** | | |
| `API_HOST` | Хост сервера | 0.0.0.0 |
| `API_PORT` | Порт сервера | 8000 |
| `API_RELOAD` | Hot reload (dev) | true |
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
| `UI_PAGE_ICON` | Иконка страницы | 🤖 |
| `USE_MOCK_API` | Использовать mock API | true |

## 📦 Стек технологий

- **Python** 3.12+
- **FastAPI** — Backend API + WebSocket
- **Uvicorn** — ASGI сервер
- **Streamlit** — UI framework
- **Pydantic** — валидация данных
- **websockets** — WebSocket клиент
- **PyYAML** — загрузка конфигурации
- **ruff** — линтинг и форматирование
- **mypy** — проверка типов
- **pytest** — тестирование
- **httpx** — HTTP клиент для тестов

## 🗺 Roadmap

- [x] Phase 1: Streamlit UI + Mock
- [x] Phase 2: FastAPI Backend + WebSocket
- [ ] Phase 3: Database (PostgreSQL + SQLAlchemy + Alembic)
- [ ] Phase 4: LLM Integration (OpenAI)
- [ ] Phase 5: RAG (Hybrid Retrieval)
- [ ] Phase 6: LangGraph Orchestration
- [ ] Phase 7: MCP Tools Integration

## 📄 Лицензия

MIT
