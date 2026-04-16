"""迁移任务主表模型"""
from sqlalchemy import Column, BigInteger, String, Enum, Integer, Numeric, DateTime, Index
from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class MigrationTask(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = 'migration_task'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_no = Column(String(32), unique=True, nullable=False, comment='任务编号')
    task_name = Column(String(128), nullable=False, default='', comment='任务名称')
    status = Column(
        Enum('draft', 'ready', 'running', 'paused', 'completed', 'failed', 'cancelled',
             name='task_status'),
        nullable=False, default='draft', comment='任务状态'
    )
    current_step = Column(
        Enum('credential', 'select_source', 'mapping', 'plan', 'execute', 'report',
             name='wizard_step'),
        nullable=False, default='credential', comment='当前向导步骤'
    )
    failure_mode = Column(
        Enum('pause', 'continue', name='failure_mode'),
        nullable=False, default='pause', comment='失败处理模式'
    )

    source_cloud = Column(String(16), nullable=False, default='aliyun')
    source_region = Column(String(32), nullable=False, default='')
    target_cloud = Column(String(16), nullable=False, default='tencent')
    target_region = Column(String(32), nullable=False, default='')
    target_mode = Column(
        Enum('existing', 'create_new', name='target_mode'),
        nullable=False, default='existing', comment='目标实例模式'
    )

    total_items = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    incompatible_count = Column(Integer, nullable=False, default=0)
    progress = Column(Numeric(5, 2), nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'task_no': self.task_no,
            'task_name': self.task_name,
            'status': self.status,
            'current_step': self.current_step,
            'failure_mode': self.failure_mode,
            'source_cloud': self.source_cloud,
            'source_region': self.source_region,
            'target_cloud': self.target_cloud,
            'target_region': self.target_region,
            'target_mode': self.target_mode,
            'total_items': self.total_items,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'incompatible_count': self.incompatible_count,
            'progress': float(self.progress) if self.progress else 0,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
