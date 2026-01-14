"""MCP logging - логирование в stderr.

ВАЖНО: MCP использует stdout для JSON-RPC протокола.
Все логи из MCP серверов должны идти в stderr.
"""

from __future__ import annotations

import logging
import sys

_configured: set[str] = set()


def get_mcp_logger(name: str) -> logging.Logger:
    """
    Получить logger для MCP модуля.
    
    Логи идут в stderr, чтобы не конфликтовать с JSON-RPC на stdout.
    
    Args:
        name: Имя модуля (обычно __name__).
        
    Returns:
        Настроенный logger.
    """
    logger = logging.getLogger(name)
    
    # Настраиваем только один раз для каждого имени
    if name not in _configured:
        logger.setLevel(logging.INFO)
        
        # Handler в stderr (НЕ stdout!)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Предотвращаем propagation к root logger
        logger.propagate = False
        
        _configured.add(name)
    
    return logger
