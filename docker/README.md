# Docker Infrastructure

## Обзор

Docker Compose конфигурация для AI Chat.

### Сервисы

| Service   | Image                    | Порт  | Profile | Описание                        |
|-----------|--------------------------|-------|---------|--------------------------------|
| postgres  | pgvector/pgvector:pg16   | 5433  | default | PostgreSQL 16 + pgvector       |
| redis     | redis:7-alpine           | 6379  | default | Redis 7 для очередей и кэша    |
| api       | ai_chat_api              | 8000  | app     | FastAPI Backend                |
| ui        | ai_chat_ui               | 8501  | app     | Streamlit Frontend             |
| adminer   | adminer:latest           | 8080  | debug   | Web UI для БД                  |

## Быстрый старт

### Вариант 1: Только БД (для локальной разработки)

```bash
# 1. Скопируйте файл окружения
cp docker/env.docker.example docker/.env

# 2. Запустите только PostgreSQL и Redis
docker compose -f docker/docker-compose.yml up -d

# 3. Примените миграции (локально)
python scripts/init_db.py

# 4. Заполните домены
python scripts/seed_domains.py

# 5. Запустите API локально
python scripts/run_api.py
```

### Вариант 2: Полный проект в Docker

```bash
# 1. Скопируйте файл окружения
cp docker/env.docker.example docker/.env

# 2. Запустите всё (БД + API + UI)
docker compose -f docker/docker-compose.yml --profile app up -d --build

# 3. Примените миграции
docker exec ai_chat_api python scripts/init_db.py

# 4. Заполните домены
docker exec ai_chat_api python scripts/seed_domains.py

# 5. Откройте приложение
# API: http://localhost:8000
# UI:  http://localhost:8501
```

## Команды

### Управление контейнерами

```bash
# Запуск в фоне
docker compose -f docker/docker-compose.yml up -d

# Остановка
docker compose -f docker/docker-compose.yml down

# Просмотр логов
docker compose -f docker/docker-compose.yml logs -f postgres

# Перезапуск
docker compose -f docker/docker-compose.yml restart postgres
```

### Запуск с Adminer (debug)

```bash
docker compose -f docker/docker-compose.yml --profile debug up -d
```

Adminer доступен на http://localhost:8080

### Подключение к PostgreSQL

```bash
# Через psql
docker exec -it ai_chat_postgres psql -U ai_chat -d ai_chat

# Проверить расширения
docker exec -it ai_chat_postgres psql -U ai_chat -d ai_chat -c "SELECT extname FROM pg_extension;"
```

### Подключение к Redis

```bash
docker exec -it ai_chat_redis redis-cli

# Проверить соединение
docker exec -it ai_chat_redis redis-cli PING
```

## Тестовая база данных

Для тестов рекомендуется создать отдельную БД:

```bash
# Создать тестовую БД
docker exec -it ai_chat_postgres psql -U ai_chat -c "CREATE DATABASE ai_chat_test;"

# Создать расширения в тестовой БД
docker exec -it ai_chat_postgres psql -U ai_chat -d ai_chat_test -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

## Переменные окружения

См. `env.docker.example` для полного списка.

| Переменная        | Default         | Описание                          |
|-------------------|-----------------|-----------------------------------|
| POSTGRES_USER     | ai_chat         | Пользователь БД                   |
| POSTGRES_PASSWORD | ai_chat_secret  | Пароль БД                         |
| POSTGRES_DB       | ai_chat         | Имя базы данных                   |
| POSTGRES_PORT     | 5433            | Порт PostgreSQL (host)            |
| REDIS_PORT        | 6379            | Порт Redis                        |
| API_PORT          | 8000            | Порт FastAPI                      |
| UI_PORT           | 8501            | Порт Streamlit                    |
| ADMINER_PORT      | 8080            | Порт Adminer (debug profile)      |

## Volumes

- `pg_data` - данные PostgreSQL (persistent)
- `redis_data` - данные Redis (persistent)

Для сброса данных:

```bash
docker compose -f docker/docker-compose.yml down -v
```

