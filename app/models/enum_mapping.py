"""枚举值映射规则模型"""
from sqlalchemy import Column, BigInteger, String, Boolean, UniqueConstraint, Index
from app.models.base import Base, TimestampMixin


class EnumMappingRule(Base, TimestampMixin):
    __tablename__ = 'enum_mapping_rule'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    category = Column(String(32), nullable=False, comment='映射分类')
    source_value = Column(String(64), nullable=False, comment='阿里云枚举值')
    target_value = Column(String(64), nullable=True, comment='腾讯云枚举值')
    is_compatible = Column(Boolean, nullable=False, default=True)
    remark = Column(String(256), nullable=True)

    __table_args__ = (
        UniqueConstraint('category', 'source_value', name='uk_category_source'),
        Index('idx_emr_category', 'category'),
    )
