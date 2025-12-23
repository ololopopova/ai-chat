-- Инициализация PostgreSQL для AI Chat
-- Этот файл выполняется при первом запуске контейнера

-- Включаем расширение pgvector для векторного поиска
CREATE EXTENSION IF NOT EXISTS vector;

-- Включаем расширение pg_trgm для нечёткого поиска
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Проверяем, что расширения установлены
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'Extension pgvector is not installed!';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        RAISE EXCEPTION 'Extension pg_trgm is not installed!';
    END IF;
    
    RAISE NOTICE 'All required extensions are installed successfully.';
END $$;

