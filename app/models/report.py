"""迁移报告和报告明细模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Enum, Text, ForeignKey, Index, JSON, DateTime
from app.models.base import Base


class MigrationReport(Base):
    __tablename__ = 'migration_report'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False, unique=True)

    total_items = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    incompatible_count = Column(Integer, nullable=False, default=0)
    total_duration_ms = Column(BigInteger, nullable=False, default=0)

    generated_at = Column(DateTime(timezone=True), nullable=False)
    report_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class ReportDetail(Base):
    __tablename__ = 'report_detail'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_id = Column(BigInteger, ForeignKey('migration_report.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(BigInteger, nullable=False)
    plan_item_id = Column(BigInteger, nullable=True)

    category = Column(
        Enum('success', 'failed', 'skipped', 'incompatible', name='report_category_enum'),
        nullable=False
    )
    operation_type = Column(String(32), nullable=False, default='')
    operation_desc = Column(String(256), nullable=False, default='')

    source_config = Column(JSON, nullable=True)
    target_config = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    incompatible_reason = Column(String(512), nullable=True)

    executed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_rd_report', 'report_id'),
        Index('idx_rd_task', 'task_id'),
        Index('idx_rd_category', 'category'),
    )
