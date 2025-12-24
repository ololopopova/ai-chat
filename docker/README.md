# Docker Infrastructure

## Быстрый старт (3 шага)

```bash
# 1. Настроить окружение
cp docker/env.docker.example docker/.env
echo "OPENAI_API_KEY=sk-ваш-ключ" >> docker/.env  # Опционально

# 2. Запустить всё
docker compose -f docker/docker-compose.yml --profile app up -d --build

# 3. Открыть
# UI:  http://localhost:8501
# API: http://localhost:8000/docs
```

> **Без API ключа** система работает в mock-режиме — можно тестировать UI.

---

## Конфигурация

**Один файл: `docker/.env`** — содержит все настройки для Docker.

### Обязательные переменные

| Переменная | Значение | Описание |
|------------|----------|----------|
| `POSTGRES_USER` | ai_chat | Пользователь БД |
| `POSTGRES_PASSWORD` | ai_chat_secret | Пароль БД |
| `POSTGRES_DB` | ai_chat | Имя базы |

### API ключи (опционально)

| Переменная | Описание |
|------------|----------|
| `OPENAI_API_KEY` | Для реальных ответов GPT-5.2 |

Без ключа — работает mock-режим.

### LLM настройки

Модели и параметры генерации настраиваются в **`config/llm.yaml`** (не в env!):

```yaml
models:
  default: "openai:gpt-5.2"
  fallback: "openai:gpt-5-mini"
generation:
  reasoning_effort: "low"
  output_verbosity: "low"
```

---

## 🔄 Hot Reload (автоперезагрузка)

### ✅ НЕ требует перезапуска контейнера:

**Изменения в коде (Python):**
- `src/**/*.py` — автоматически подхватываются (uvicorn reload)
- `ui/**/*.py` — автоматически подхватываются (streamlit rerun)
- `config/*.yaml` — подхватываются при следующем запросе

Просто сохрани файл — изменения применятся через 1-2 секунды!

### ⚠️ Требует перезапуска контейнера:

**Изменения в зависимостях:**
- `requirements.txt` → нужен rebuild
- `alembic/` миграции → нужен `alembic upgrade head`

```bash
# Если менял requirements.txt
docker compose -f docker/docker-compose.yml --profile app up -d --build

# Если добавил миграции
docker exec ai_chat_api alembic upgrade head
```

---

## Сервисы

| Service | Порт | Profile | Описание |
|---------|------|---------|----------|
| postgres | 5433 | default | PostgreSQL 16 + pgvector |
| redis | 6379 | default | Redis 7 |
| api | 8000 | app | FastAPI Backend |
| ui | 8501 | app | Streamlit Frontend |
| adminer | 8080 | debug | Web UI для БД |

---

## Команды

### Запуск

```bash
# Только БД + Redis (для локальной разработки)
docker compose -f docker/docker-compose.yml up -d

# Полный стек (БД + API + UI)
docker compose -f docker/docker-compose.yml --profile app up -d

# С пересборкой образов
docker compose -f docker/docker-compose.yml --profile app up -d --build

# С Adminer (debug)
docker compose -f docker/docker-compose.yml --profile debug up -d
```

### Управление

```bash
# Статус
docker compose -f docker/docker-compose.yml ps

# Логи
docker compose -f docker/docker-compose.yml logs -f api

# Перезапуск (после изменения .env)
docker compose -f docker/docker-compose.yml restart api

# Остановка
docker compose -f docker/docker-compose.yml down

# Удалить с данными
docker compose -f docker/docker-compose.yml down -v
```

### База данных

```bash
# Применить миграции
docker exec ai_chat_api alembic upgrade head

# Заполнить домены
docker exec ai_chat_api python scripts/seed_domains.py

# Подключиться к PostgreSQL
docker exec -it ai_chat_postgres psql -U ai_chat -d ai_chat

# Подключиться к Redis
docker exec -it ai_chat_redis redis-cli
```

---

## Volumes

| Volume | Описание |
|--------|----------|
| `pg_data` | Данные PostgreSQL (persistent) |
| `redis_data` | Данные Redis (persistent) |

---

## Troubleshooting

### API не отвечает
```bash
docker compose -f docker/docker-compose.yml logs api
```

### Сбросить всё и начать заново
```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml --profile app up -d --build
docker exec ai_chat_api alembic upgrade head
```
