"""迁移计划项模型"""
from sqlalchemy import Column, BigInteger, String, Integer, Enum, Boolean, ForeignKey, Index, JSON, DateTime, Text
from app.models.base import Base, TimestampMixin


class MigrationPlanItem(Base, TimestampMixin):
    __tablename__ = 'migration_plan_item'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False)
    mapping_result_id = Column(BigInteger, nullable=True)
    mapping_id = Column(BigInteger, ForeignKey('instance_mapping.id', ondelete='CASCADE'), nullable=False)

    seq_no = Column(Integer, nullable=False)
    operation_type = Column(
        Enum('create_instance', 'create_listener', 'create_rule',
             'modify_listener', 'modify_rule', 'set_health_check',
             'set_acl', 'set_timeout', 'set_session', 'set_bandwidth',
             name='operation_type_enum'),
        nullable=False
    )
    operation_desc = Column(String(256), nullable=False, default='')

    target_instance_id = Column(String(64), nullable=False, default='')
    request_params = Column(JSON, nullable=False)

    has_conflict = Column(Boolean, nullable=False, default=False)
    conflict_detail = Column(JSON, nullable=True)
    conflict_action = Column(
        Enum('overwrite', 'skip', 'create_new', name='conflict_action_enum'),
        nullable=True
    )

    status = Column(
        Enum('pending', 'waiting_confirm', 'confirmed', 'running',
             'success', 'failed', 'skipped', 'cancelled',
             name='plan_item_status_enum'),
        nullable=False, default='pending'
    )
    user_confirmed = Column(Boolean, nullable=False, default=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    executed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    response_data = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index('idx_plan_task', 'task_id'),
        Index('idx_plan_task_seq', 'task_id', 'seq_no'),
        Index('idx_plan_status', 'status'),
    )
