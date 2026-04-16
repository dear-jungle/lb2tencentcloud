"""映射结果和不兼容项模型"""
from sqlalchemy import Column, BigInteger, String, Enum, ForeignKey, Index, JSON
from app.models.base import Base, TimestampMixin


class MappingResult(Base, TimestampMixin):
    __tablename__ = 'mapping_result'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False)
    mapping_id = Column(BigInteger, ForeignKey('instance_mapping.id', ondelete='CASCADE'), nullable=False)

    source_type = Column(
        Enum('listener', 'forwarding_rule', 'health_check', 'acl', 'session', 'timeout', 'bandwidth',
             name='source_type_enum'),
        nullable=False
    )
    source_ref_id = Column(BigInteger, nullable=True)
    source_description = Column(String(256), nullable=False, default='')

    mapping_status = Column(
        Enum('mapped', 'incompatible', 'partial', 'manual', name='mapping_status_enum'),
        nullable=False, default='mapped'
    )
    source_config = Column(JSON, nullable=False)
    target_config = Column(JSON, nullable=True)
    diff_summary = Column(String(512), nullable=True)

    user_action = Column(
        Enum('accept', 'skip', 'modify', name='user_action_enum'),
        nullable=False, default='accept'
    )
    user_modified_config = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_mr_task_id', 'task_id'),
        Index('idx_mr_mapping_id', 'mapping_id'),
        Index('idx_mr_status', 'mapping_status'),
    )


class IncompatibleItem(Base):
    __tablename__ = 'incompatible_item'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False)
    mapping_result_id = Column(BigInteger, ForeignKey('mapping_result.id', ondelete='CASCADE'), nullable=False)

    config_name = Column(String(128), nullable=False)
    source_value = Column(String(512), nullable=False, default='')
    reason = Column(String(512), nullable=False)
    severity = Column(
        Enum('error', 'warning', 'info', name='severity_enum'),
        nullable=False, default='warning'
    )
    suggestion = Column(String(512), nullable=True)
    created_at = Column(BigInteger, nullable=True)  # will use TimestampMixin pattern

    __table_args__ = (
        Index('idx_inc_task', 'task_id'),
        Index('idx_inc_mr', 'mapping_result_id'),
    )
