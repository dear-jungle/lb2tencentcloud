"""源端配置快照和子表模型"""
from sqlalchemy import Column, BigInteger, String, Integer, Enum, ForeignKey, Index, JSON, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class SourceClbSnapshot(Base):
    __tablename__ = 'source_clb_snapshot'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    mapping_id = Column(BigInteger, ForeignKey('instance_mapping.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(BigInteger, ForeignKey('migration_task.id', ondelete='CASCADE'), nullable=False)
    instance_id = Column(String(64), nullable=False)

    raw_config = Column(JSON, nullable=False)
    listeners_config = Column(JSON, nullable=True)
    health_check_config = Column(JSON, nullable=True)
    forwarding_rules = Column(JSON, nullable=True)
    advanced_params = Column(JSON, nullable=True)
    acl_policies = Column(JSON, nullable=True)
    bandwidth_config = Column(JSON, nullable=True)

    snapshot_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_snap_task_id', 'task_id'),
        Index('idx_snap_mapping_id', 'mapping_id'),
        Index('idx_snap_instance_id', 'instance_id'),
    )


class SourceListener(Base):
    __tablename__ = 'source_listener'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_id = Column(BigInteger, ForeignKey('source_clb_snapshot.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(BigInteger, nullable=False)
    instance_id = Column(String(64), nullable=False)

    listener_port = Column(Integer, nullable=False)
    listener_protocol = Column(String(8), nullable=False)
    backend_port = Column(Integer, nullable=True)
    scheduler = Column(String(32), nullable=False, default='')
    status = Column(String(16), nullable=False, default='')

    connection_timeout = Column(Integer, nullable=True)
    idle_timeout = Column(Integer, nullable=True)
    request_timeout = Column(Integer, nullable=True)

    sticky_session = Column(Enum('on', 'off', name='sticky_enum'), nullable=False, default='off')
    sticky_session_type = Column(String(16), nullable=True)
    cookie_timeout = Column(Integer, nullable=True)
    cookie = Column(String(128), nullable=True)

    bandwidth = Column(Integer, nullable=True)
    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_listener_snapshot', 'snapshot_id'),
        Index('idx_listener_task', 'task_id'),
        Index('idx_listener_port_proto', 'instance_id', 'listener_port', 'listener_protocol'),
    )


class SourceForwardingRule(Base):
    __tablename__ = 'source_forwarding_rule'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    listener_id = Column(BigInteger, ForeignKey('source_listener.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(BigInteger, nullable=False)

    rule_id = Column(String(64), nullable=False, default='')
    domain = Column(String(256), nullable=False, default='')
    url_path = Column(String(512), nullable=False, default='')
    scheduler = Column(String(32), nullable=True)

    sticky_session = Column(Enum('on', 'off', name='rule_sticky_enum'), nullable=True)
    sticky_session_type = Column(String(16), nullable=True)
    cookie_timeout = Column(Integer, nullable=True)
    health_check_enabled = Column(Enum('on', 'off', name='rule_hc_enum'), nullable=True)

    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_rule_listener', 'listener_id'),
        Index('idx_rule_task', 'task_id'),
    )


class SourceHealthCheck(Base):
    __tablename__ = 'source_health_check'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    listener_id = Column(BigInteger, ForeignKey('source_listener.id', ondelete='CASCADE'), nullable=False)
    rule_id = Column(BigInteger, nullable=True)

    health_check_enabled = Column(Enum('on', 'off', name='hc_enabled_enum'), nullable=False, default='on')
    check_type = Column(String(8), nullable=True)
    check_port = Column(Integer, nullable=True)
    check_path = Column(String(256), nullable=True)
    check_domain = Column(String(256), nullable=True)
    check_interval = Column(Integer, nullable=True)
    check_timeout = Column(Integer, nullable=True)
    healthy_threshold = Column(Integer, nullable=True)
    unhealthy_threshold = Column(Integer, nullable=True)
    http_code = Column(String(64), nullable=True)

    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_hc_listener', 'listener_id'),
    )


class SourceAclPolicy(Base):
    __tablename__ = 'source_acl_policy'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_id = Column(BigInteger, ForeignKey('source_clb_snapshot.id', ondelete='CASCADE'), nullable=False)
    listener_id = Column(BigInteger, nullable=True)

    acl_id = Column(String(64), nullable=False, default='')
    acl_name = Column(String(128), nullable=False, default='')
    acl_type = Column(String(16), nullable=False, default='')
    acl_entries = Column(JSON, nullable=True)

    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_acl_snapshot', 'snapshot_id'),
    )
