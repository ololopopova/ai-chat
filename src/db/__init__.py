"""Database layer для AI Chat.

Содержит:
- engine.py - Async SQLAlchemy engine factory
- session.py - AsyncSession factory
- base.py - Base model class
- models/ - ORM модели
"""

from src.db.base import Base
from src.db.engine import get_engine
from src.db.session import AsyncSessionFactory, get_session

__all__ = [
    "AsyncSessionFactory",
    "Base",
    "get_engine",
    "get_session",
]
