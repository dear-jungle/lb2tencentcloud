"""统一配置数据模型（中间格式）

阿里云和腾讯云 CLB 配置均转换为此格式，
映射引擎基于中间格式进行字段级映射。
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ListenerConfig:
    """监听器统一模型"""
    port: int
    protocol: str                           # TCP/UDP/HTTP/HTTPS
    backend_port: Optional[int] = None
    scheduler: str = ''                     # wrr/wlc/rr (阿里云) 或 WRR/LEAST_CONN (腾讯云)
    status: str = ''
    bandwidth: int = -1                     # -1 表示不限

    # 超时参数
    connection_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    request_timeout: Optional[int] = None

    # 会话保持
    sticky_session: str = 'off'             # on/off
    sticky_session_type: Optional[str] = None  # insert/server (阿里) 或 NORMAL/CUSTOMIZED (腾讯)
    cookie_timeout: Optional[int] = None
    cookie: Optional[str] = None

    # 健康检查
    health_check: Optional['HealthCheckConfig'] = None

    # 转发规则
    forwarding_rules: list = field(default_factory=list)

    # ACL
    acl_status: str = 'off'
    acl_type: Optional[str] = None          # white/black
    acl_id: Optional[str] = None
    acl_entries: list = field(default_factory=list)

    # 原始数据（用于审计）
    raw: dict = field(default_factory=dict)

    @property
    def description(self):
        return f'{self.protocol.upper()}:{self.port}'


@dataclass
class HealthCheckConfig:
    """健康检查统一模型"""
    enabled: str = 'on'                     # on/off
    check_type: Optional[str] = None        # TCP/HTTP
    check_port: Optional[int] = None
    check_path: Optional[str] = None
    check_domain: Optional[str] = None
    check_interval: Optional[int] = None    # 秒
    check_timeout: Optional[int] = None     # 秒
    healthy_threshold: Optional[int] = None
    unhealthy_threshold: Optional[int] = None
    http_code: Optional[str] = None         # 如 http_2xx,http_3xx


@dataclass
class ForwardingRuleConfig:
    """转发规则统一模型"""
    rule_id: str = ''
    domain: str = ''
    url_path: str = ''
    scheduler: Optional[str] = None
    sticky_session: Optional[str] = None
    sticky_session_type: Optional[str] = None
    cookie_timeout: Optional[int] = None
    health_check_enabled: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class AclEntry:
    """ACL 条目"""
    cidr: str = ''
    comment: str = ''


@dataclass
class ClbInstanceConfig:
    """CLB 实例完整配置（中间格式）"""
    instance_id: str = ''
    instance_name: str = ''
    address: str = ''                       # VIP
    address_type: str = ''                  # internet/intranet
    network_type: str = ''                  # classic/vpc
    vpc_id: str = ''
    listeners: list = field(default_factory=list)   # List[ListenerConfig]
    cloud: str = ''                         # aliyun/tencent
    region: str = ''
    raw: dict = field(default_factory=dict)


@dataclass
class MappingItem:
    """单项映射结果"""
    source_type: str                        # listener/forwarding_rule/health_check/acl/session/timeout/bandwidth
    source_description: str
    source_config: dict
    target_config: Optional[dict] = None
    status: str = 'mapped'                  # mapped/incompatible/partial
    diff_summary: str = ''
    incompatible_items: list = field(default_factory=list)  # List[IncompatibleDetail]


@dataclass
class IncompatibleDetail:
    """不兼容项详情"""
    config_name: str
    source_value: str
    reason: str
    severity: str = 'warning'               # error/warning/info
    suggestion: str = ''
    recommendation: str = ''                # 自动推荐的替代值
    alternatives: list = field(default_factory=list)  # 所有可选替代方案 [{value, label}]
