"""SQLAlchemy 模型基类和 Mixin"""
from datetime import datetime, timezone

from sqlalchemy import Column, BigInteger, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """时间戳 Mixin — 自动管理 created_at / updated_at"""
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class SoftDeleteMixin:
    """软删除 Mixin"""
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
