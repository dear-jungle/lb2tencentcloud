"""执行日志模型"""
from sqlalchemy import Column, BigInteger, Enum, Text, ForeignKey, Index, JSON, DateTime
from app.models.base import Base


class ExecutionLog(Base):
    __tablename__ = 'execution_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False)
    plan_item_id = Column(BigInteger, nullable=True)

    log_level = Column(
        Enum('info', 'warn', 'error', 'debug', name='log_level_enum'),
        nullable=False, default='info'
    )
    log_type = Column(
        Enum('system', 'api_call', 'user_action', 'confirm', 'error', 'progress',
             name='log_type_enum'),
        nullable=False, default='system'
    )
    message = Column(Text, nullable=False)
    detail = Column(JSON, nullable=True)
    logged_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_log_task', 'task_id'),
        Index('idx_log_task_time', 'task_id', 'logged_at'),
    )
