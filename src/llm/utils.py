"""Утилиты для работы с LLM ответами."""

from __future__ import annotations

from typing import Any


def extract_text_from_response(content: Any) -> str:
    """
    Извлечь текст из ответа LLM.

    GPT-5.x возвращает content как список блоков:
    [
        {'type': 'reasoning', 'summary': [], ...},
        {'type': 'text', 'text': 'ответ', ...}
    ]

    Старые модели возвращают просто строку.

    Args:
        content: Содержимое ответа (строка или список блоков)

    Returns:
        Извлечённый текст
    """
    # Если уже строка — возвращаем как есть
    if isinstance(content, str):
        return content

    # Если список блоков (GPT-5.x формат)
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                # Ищем блоки с текстом
                if block.get("type") == "text" and "text" in block:
                    text_parts.append(block["text"])
                # Альтернативный формат
                elif "content" in block:
                    text_parts.append(str(block["content"]))
            elif isinstance(block, str):
                text_parts.append(block)

        return " ".join(text_parts) if text_parts else ""

    # Fallback — преобразуем в строку
    return str(content) if content else ""
