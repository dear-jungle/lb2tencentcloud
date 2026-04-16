"""实例映射关系模型"""
from sqlalchemy import Column, BigInteger, String, Enum, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class InstanceMapping(Base, TimestampMixin):
    __tablename__ = 'instance_mapping'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False)

    source_instance_id = Column(String(64), nullable=False)
    source_instance_name = Column(String(128), nullable=False, default='')
    source_vip = Column(String(64), nullable=False, default='')
    source_network_type = Column(String(16), nullable=False, default='')
    source_status = Column(String(16), nullable=False, default='')

    target_instance_id = Column(String(64), nullable=False, default='')
    target_instance_name = Column(String(128), nullable=False, default='')
    target_vip = Column(String(64), nullable=False, default='')
    target_created_by_system = Column(Boolean, nullable=False, default=False)

    mapping_type = Column(
        Enum('one_to_one', 'many_to_one', name='mapping_type_enum'),
        nullable=False, default='one_to_one'
    )

    __table_args__ = (
        Index('idx_im_task_id', 'task_id'),
        Index('idx_im_source', 'source_instance_id'),
        Index('idx_im_target', 'target_instance_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'source_instance_id': self.source_instance_id,
            'source_instance_name': self.source_instance_name,
            'source_vip': self.source_vip,
            'source_network_type': self.source_network_type,
            'target_instance_id': self.target_instance_id,
            'target_instance_name': self.target_instance_name,
            'target_vip': self.target_vip,
            'target_created_by_system': self.target_created_by_system,
            'mapping_type': self.mapping_type,
        }
