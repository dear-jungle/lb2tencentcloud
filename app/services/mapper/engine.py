"""配置映射引擎 — 阿里云 CLB → 腾讯云 CLB

基于规则的映射引擎，字段级映射 + 枚举值转换表。
"""
import logging
from typing import Optional
from app.services.mapper.models import (
    ListenerConfig, HealthCheckConfig, ForwardingRuleConfig,
    MappingItem, IncompatibleDetail
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────
# 枚举值映射表（静态，与 init.sql 一致）
# ──────────────────────────────────────

SCHEDULER_MAP = {
    'wrr': ('WRR', True, '加权轮询'),
    'wlc': ('LEAST_CONN', True, '加权最小连接数'),
    'rr':  ('WRR', True, '轮询 → 加权轮询（权重均等）'),
    'sch': (None, False, '源地址哈希，腾讯云 CLB 不支持'),
    'tch': (None, False, '四元组哈希，腾讯云 CLB 不支持'),
    'qch': (None, False, '五元组哈希，腾讯云 CLB 不支持'),
}

# 不兼容调度算法的推荐替代（功能最接近优先）
SCHEDULER_RECOMMENDATION = {
    'sch': ('WRR', [
        {'value': 'WRR', 'label': 'WRR (加权轮询)'},
        {'value': 'LEAST_CONN', 'label': 'LEAST_CONN (最小连接数)'},
    ]),
    'tch': ('WRR', [
        {'value': 'WRR', 'label': 'WRR (加权轮询)'},
        {'value': 'LEAST_CONN', 'label': 'LEAST_CONN (最小连接数)'},
    ]),
    'qch': ('LEAST_CONN', [
        {'value': 'LEAST_CONN', 'label': 'LEAST_CONN (最小连接数)'},
        {'value': 'WRR', 'label': 'WRR (加权轮询)'},
    ]),
}

PROTOCOL_MAP = {
    'tcp':   ('TCP', True),
    'udp':   ('UDP', True),
    'http':  ('HTTP', True),
    'https': ('HTTPS', True),
}

HEALTH_CHECK_TYPE_MAP = {
    'tcp':  ('TCP', True),
    'http': ('HTTP', True),
}

STICKY_SESSION_TYPE_MAP = {
    'insert': ('NORMAL', True, '植入 Cookie → 腾讯云 CLB 管理的 Cookie'),
    'server': ('CUSTOMIZED', True, '重写 Cookie → 自定义 Cookie'),
}

ACL_TYPE_MAP = {
    'white': ('white', True),
    'black': ('black', True),
}


class ConfigMappingEngine:
    """配置映射引擎"""

    def map_listener(self, listener: dict) -> MappingItem:
        """映射单个监听器配置"""
        incompatibles = []
        source_proto = listener.get('listener_protocol', '').lower()
        source_scheduler = listener.get('scheduler', '').lower()

        # 协议映射
        proto_entry = PROTOCOL_MAP.get(source_proto)
        if not proto_entry:
            incompatibles.append(IncompatibleDetail(
                config_name='listener_protocol',
                source_value=source_proto,
                reason=f'协议类型 "{source_proto}" 在腾讯云 CLB 不支持',
                severity='error',
            ))
            return MappingItem(
                source_type='listener',
                source_description=f'{source_proto.upper()}:{listener.get("listener_port", "?")}',
                source_config=listener,
                status='incompatible',
                diff_summary=f'协议 {source_proto} 不兼容',
                incompatible_items=incompatibles,
            )

        target_proto = proto_entry[0]

        # 调度算法映射
        target_scheduler = None
        sched_entry = SCHEDULER_MAP.get(source_scheduler)
        if sched_entry:
            target_scheduler, compatible, remark = sched_entry
            if not compatible:
                rec = SCHEDULER_RECOMMENDATION.get(source_scheduler, ('WRR', []))
                recommendation = rec[0]
                alternatives = rec[1] if len(rec) > 1 else []
                target_scheduler = recommendation  # 自动填充推荐值
                incompatibles.append(IncompatibleDetail(
                    config_name='scheduler',
                    source_value=source_scheduler,
                    reason=remark,
                    severity='warning',
                    suggestion=f'推荐使用 {recommendation}',
                    recommendation=recommendation,
                    alternatives=alternatives,
                ))
        elif source_scheduler:
            incompatibles.append(IncompatibleDetail(
                config_name='scheduler',
                source_value=source_scheduler,
                reason=f'未知调度算法 "{source_scheduler}"',
                severity='warning',
            ))

        # 会话保持映射
        target_sticky = self._map_sticky_session(listener, incompatibles)

        # 健康检查映射
        target_health_check = self._map_health_check(listener, incompatibles)

        # 超时参数映射
        target_timeout = self._map_timeout(listener, incompatibles)

        # 带宽映射
        target_bandwidth = self._map_bandwidth(listener, incompatibles)

        # ACL 映射
        target_acl = self._map_acl(listener, incompatibles)

        # 组装目标配置
        target_config = {
            'Protocol': target_proto,
            'ListenerPort': listener.get('listener_port'),
            'Scheduler': target_scheduler or 'WRR',
            **target_sticky,
            **target_health_check,
            **target_timeout,
            **target_bandwidth,
            **target_acl,
        }

        status = 'incompatible' if any(i.severity == 'error' for i in incompatibles) else \
                 'partial' if incompatibles else 'mapped'

        return MappingItem(
            source_type='listener',
            source_description=f'{source_proto.upper()}:{listener.get("listener_port", "?")}',
            source_config=listener,
            target_config=target_config,
            status=status,
            diff_summary=f'{len(incompatibles)} 个不兼容项' if incompatibles else '完全映射',
            incompatible_items=incompatibles,
        )

    def map_forwarding_rule(self, rule: dict) -> MappingItem:
        """映射单个转发规则"""
        incompatibles = []

        target_config = {
            'Domain': rule.get('domain', ''),
            'Url': rule.get('url', '') or rule.get('url_path', '') or '/',  # 腾讯云要求 Url 非空
        }

        if rule.get('scheduler'):
            sched_entry = SCHEDULER_MAP.get(rule['scheduler'].lower())
            if sched_entry and sched_entry[1]:
                target_config['Scheduler'] = sched_entry[0]
            elif sched_entry:
                incompatibles.append(IncompatibleDetail(
                    config_name='rule_scheduler',
                    source_value=rule['scheduler'],
                    reason=sched_entry[2],
                    severity='warning',
                ))

        return MappingItem(
            source_type='forwarding_rule',
            source_description=f'{rule.get("domain", "*")}:{rule.get("url", "") or rule.get("url_path", "") or "/"}',
            source_config=rule,
            target_config=target_config,
            status='partial' if incompatibles else 'mapped',
            diff_summary=f'{len(incompatibles)} 个不兼容项' if incompatibles else '完全映射',
            incompatible_items=incompatibles,
        )

    def _map_sticky_session(self, listener: dict, incompatibles: list) -> dict:
        """映射会话保持"""
        result = {}
        if listener.get('sticky_session') == 'on':
            src_type = (listener.get('sticky_session_type') or '').lower()
            entry = STICKY_SESSION_TYPE_MAP.get(src_type)
            if entry:
                result['SessionExpireTime'] = listener.get('cookie_timeout', 0)
                result['StickySessionType'] = entry[0]
            elif src_type:
                incompatibles.append(IncompatibleDetail(
                    config_name='sticky_session_type',
                    source_value=src_type,
                    reason=f'会话保持类型 "{src_type}" 无法映射',
                    severity='warning',
                ))
        return result

    def _map_health_check(self, listener: dict, incompatibles: list) -> dict:
        """映射健康检查"""
        result = {}
        hc_on = listener.get('health_check', 'off')
        if hc_on == 'on':
            result['HealthCheck'] = 1

            hc_type = (listener.get('health_check_type') or '').lower()
            type_entry = HEALTH_CHECK_TYPE_MAP.get(hc_type)
            if type_entry:
                result['HealthCheckType'] = type_entry[0]
            elif hc_type:
                incompatibles.append(IncompatibleDetail(
                    config_name='health_check_type',
                    source_value=hc_type,
                    reason=f'健康检查类型 "{hc_type}" 不支持',
                    severity='warning',
                ))

            if listener.get('health_check_domain'):
                result['HealthCheckDomain'] = listener['health_check_domain']
            if listener.get('health_check_uri'):
                result['HealthCheckHttpPath'] = listener['health_check_uri']
            if listener.get('health_check_connect_port'):
                result['HealthCheckPort'] = listener['health_check_connect_port']

            # 间隔和阈值 — 腾讯云范围校验
            interval = listener.get('health_check_interval')
            if interval is not None:
                if 2 <= interval <= 300:
                    result['HealthCheckIntervalTime'] = interval
                else:
                    incompatibles.append(IncompatibleDetail(
                        config_name='health_check_interval',
                        source_value=str(interval),
                        reason=f'健康检查间隔 {interval}s 超出腾讯云范围 [2-300]',
                        severity='warning',
                        suggestion='将自动调整为最近的合法值',
                    ))
                    result['HealthCheckIntervalTime'] = max(2, min(300, interval))

            timeout = listener.get('health_check_timeout')
            if timeout is not None:
                if 2 <= timeout <= 60:
                    result['HealthCheckTimeOut'] = timeout
                else:
                    incompatibles.append(IncompatibleDetail(
                        config_name='health_check_timeout',
                        source_value=str(timeout),
                        reason=f'健康检查超时 {timeout}s 超出腾讯云范围 [2-60]',
                        severity='warning',
                        suggestion='将自动调整为最近的合法值',
                    ))
                    result['HealthCheckTimeOut'] = max(2, min(60, timeout))

            if listener.get('healthy_threshold') is not None:
                result['HealthNum'] = listener['healthy_threshold']
            if listener.get('unhealthy_threshold') is not None:
                result['UnHealthNum'] = listener['unhealthy_threshold']

            # HTTP 状态码转换
            http_code = listener.get('health_check_http_code', '')
            if http_code:
                code_map = {
                    'http_2xx': 1, 'http_3xx': 2, 'http_4xx': 4, 'http_5xx': 8,
                }
                code_val = 0
                for part in http_code.split(','):
                    code_val |= code_map.get(part.strip().lower(), 0)
                if code_val > 0:
                    result['HealthCheckHttpCode'] = code_val
        else:
            result['HealthCheck'] = 0
        return result

    def _map_timeout(self, listener: dict, incompatibles: list) -> dict:
        """映射超时参数"""
        result = {}
        idle = listener.get('idle_timeout')
        if idle is not None:
            result['IdleConnectTimeout'] = idle

        req_timeout = listener.get('request_timeout')
        if req_timeout is not None:
            result['RequestTimeout'] = req_timeout

        return result

    def _map_bandwidth(self, listener: dict, incompatibles: list) -> dict:
        """映射带宽限制"""
        result = {}
        bw = listener.get('bandwidth')
        if bw is not None and bw != -1:
            result['Bandwidth'] = bw
        return result

    def _map_acl(self, listener: dict, incompatibles: list) -> dict:
        """映射 ACL 策略"""
        result = {}
        if listener.get('acl_status') == 'on':
            acl_type = (listener.get('acl_type') or '').lower()
            entry = ACL_TYPE_MAP.get(acl_type)
            if entry:
                result['AclType'] = entry[0]
            elif acl_type:
                incompatibles.append(IncompatibleDetail(
                    config_name='acl_type',
                    source_value=acl_type,
                    reason=f'ACL 类型 "{acl_type}" 无法映射',
                    severity='warning',
                ))
        return result

    def map_full_config(self, listeners: list) -> list:
        """映射完整实例配置 — 返回所有映射结果列表（扁平，向后兼容）"""
        results = []
        for listener in listeners:
            listener_result = self.map_listener(listener)
            results.append(listener_result)
            for rule in listener.get('forwarding_rules', []):
                rule_result = self.map_forwarding_rule(rule)
                results.append(rule_result)
        return results

    def map_by_instance(self, instance_mappings: list) -> dict:
        """按实例分组映射 — 返回 {sourceId: {targetId, sourceName, targetName, results[]}}

        参数 instance_mappings: [{sourceId, targetId, sourceName, targetName, listeners}]
        """
        grouped = {}
        for mapping in instance_mappings:
            source_id = mapping.get('sourceId', '')
            listeners = mapping.get('listeners', [])
            results = self.map_full_config(listeners)

            grouped[source_id] = {
                'sourceId': source_id,
                'targetId': mapping.get('targetId', ''),
                'sourceName': mapping.get('sourceName', ''),
                'targetName': mapping.get('targetName', ''),
                'results': results,
                'summary': {
                    'total': len(results),
                    'mapped': sum(1 for r in results if r.status == 'mapped'),
                    'partial': sum(1 for r in results if r.status == 'partial'),
                    'incompatible': sum(1 for r in results if r.status == 'incompatible'),
                },
            }
        return grouped

    def detect_port_conflicts(self, all_listeners: list) -> list:
        """检测多对一映射时的端口冲突"""
        port_map = {}
        conflicts = []
        for listener in all_listeners:
            key = (listener.get('listener_protocol', '').lower(), listener.get('listener_port'))
            if key in port_map:
                conflicts.append({
                    'protocol': key[0],
                    'port': key[1],
                    'existing': port_map[key],
                    'conflicting': listener,
                })
            else:
                port_map[key] = listener
        return conflicts
