"""腾讯云 CLB 写入服务 — 仅封装 Create 类 API"""
import logging
import json
import time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models as clb_models

logger = logging.getLogger(__name__)


class TencentClbWriter:
    """腾讯云 CLB 写入服务

    安全约束：
    - 只封装 Create 类 API（不做 Modify/Delete）
    - 每次写操作前必须已经过用户确认
    """

    def __init__(self, secret_id, secret_key, region='ap-guangzhou'):
        self._cred = credential.Credential(secret_id, secret_key)
        self._region = region
        self._client = clb_client.ClbClient(self._cred, region)

    # ─── 1.1 创建监听器 ──────────────────────────────────────────

    def create_listener(self, lb_id, params):
        """创建 CLB 监听器

        Args:
            lb_id: 负载均衡实例 ID
            params: {
                'Protocol': 'TCP'|'UDP'|'HTTP'|'HTTPS',
                'ListenerPort': 80,
                'ListenerName': '...',
                'Scheduler': 'WRR'|'LEAST_CONN',
                'SessionExpireTime': 0,
                'HealthCheck': {...} (可选),
            }

        Returns:
            {'listener_ids': [...], 'request_id': '...'}

        Raises:
            ValueError: API 调用失败
        """
        try:
            req = clb_models.CreateListenerRequest()
            req.LoadBalancerId = lb_id

            protocol = params.get('Protocol', 'TCP').upper()
            port = int(params.get('ListenerPort', 80))

            req.Ports = [port]
            req.Protocol = protocol
            req.ListenerNames = [params.get('ListenerName', f'{protocol}:{port}')]

            # 调度算法
            scheduler = params.get('Scheduler', 'WRR')
            if scheduler:
                req.Scheduler = scheduler

            # 会话保持
            session_time = params.get('SessionExpireTime')
            if session_time and int(session_time) > 0:
                req.SessionExpireTime = int(session_time)

            # 健康检查（仅 TCP/UDP 支持在创建时设置）
            hc = params.get('HealthCheck')
            if hc and protocol in ('TCP', 'UDP'):
                health = clb_models.HealthCheck()
                health.HealthSwitch = hc.get('HealthSwitch', 0)
                if hc.get('TimeOut'):
                    health.TimeOut = int(hc['TimeOut'])
                if hc.get('IntervalTime'):
                    health.IntervalTime = int(hc['IntervalTime'])
                if hc.get('HealthNum'):
                    health.HealthNum = int(hc['HealthNum'])
                if hc.get('UnHealthNum'):
                    health.UnHealthNum = int(hc['UnHealthNum'])
                req.HealthCheck = health

            logger.info(f'创建监听器: lb={lb_id}, protocol={protocol}, port={port}, scheduler={scheduler}')
            response = self._client.CreateListener(req)
            result = json.loads(response.to_json_string())

            listener_ids = result.get('ListenerIds', [])
            request_id = result.get('RequestId', '')
            logger.info(f'监听器创建成功: {listener_ids}, request_id={request_id}')

            return {
                'listener_ids': listener_ids,
                'request_id': request_id,
            }

        except TencentCloudSDKException as e:
            logger.error(f'创建监听器失败: {e.code} - {e.message}')
            raise ValueError(f'创建监听器失败: [{e.code}] {e.message}')

    # ─── 1.2 创建转发规则 ────────────────────────────────────────

    def create_rule(self, lb_id, listener_id, params):
        """创建七层转发规则（HTTP/HTTPS 监听器）

        Args:
            lb_id: 负载均衡实例 ID
            listener_id: 监听器 ID
            params: {
                'Domain': 'www.example.com',
                'Url': '/api',
                'Scheduler': 'WRR',
                'SessionExpireTime': 0,
                'HealthCheck': {...} (可选),
            }

        Returns:
            {'location_ids': [...], 'request_id': '...'}
        """
        try:
            req = clb_models.CreateRuleRequest()
            req.LoadBalancerId = lb_id
            req.ListenerId = listener_id

            rule = clb_models.RuleInput()
            rule.Domain = params.get('Domain', '')
            rule.Url = params.get('Url', '/')

            scheduler = params.get('Scheduler', 'WRR')
            if scheduler:
                rule.Scheduler = scheduler

            session_time = params.get('SessionExpireTime')
            if session_time and int(session_time) > 0:
                rule.SessionExpireTime = int(session_time)

            # 健康检查
            hc = params.get('HealthCheck')
            if hc:
                health = clb_models.HealthCheck()
                health.HealthSwitch = hc.get('HealthSwitch', 0)
                if hc.get('TimeOut'):
                    health.TimeOut = int(hc['TimeOut'])
                if hc.get('IntervalTime'):
                    health.IntervalTime = int(hc['IntervalTime'])
                rule.HealthCheck = health

            req.Rules = [rule]

            logger.info(f'创建转发规则: lb={lb_id}, listener={listener_id}, '
                        f'domain={rule.Domain}, url={rule.Url}')
            response = self._client.CreateRule(req)
            result = json.loads(response.to_json_string())

            location_ids = result.get('LocationIds', [])
            request_id = result.get('RequestId', '')
            logger.info(f'转发规则创建成功: {location_ids}, request_id={request_id}')

            return {
                'location_ids': location_ids,
                'request_id': request_id,
            }

        except TencentCloudSDKException as e:
            logger.error(f'创建转发规则失败: {e.code} - {e.message}')
            raise ValueError(f'创建转发规则失败: [{e.code}] {e.message}')

    # ─── 1.3 查询已有监听器（冲突检测用）──────────────────────────

    def describe_listeners(self, lb_id):
        """查询目标实例的所有监听器

        Returns:
            [{'ListenerId': '...', 'Protocol': 'TCP', 'Port': 80, 'ListenerName': '...'}, ...]
        """
        try:
            req = clb_models.DescribeListenersRequest()
            req.LoadBalancerId = lb_id

            response = self._client.DescribeListeners(req)
            result = json.loads(response.to_json_string())

            listeners = []
            for ls in result.get('Listeners', []):
                listeners.append({
                    'ListenerId': ls.get('ListenerId', ''),
                    'Protocol': ls.get('Protocol', ''),
                    'Port': ls.get('Port', 0),
                    'ListenerName': ls.get('ListenerName', ''),
                })

            logger.info(f'查询监听器: lb={lb_id}, 数量={len(listeners)}')
            return listeners

        except TencentCloudSDKException as e:
            logger.error(f'查询监听器失败: {e.code} - {e.message}')
            raise ValueError(f'查询监听器失败: [{e.code}] {e.message}')

    # ─── 1.4 冲突检测 ────────────────────────────────────────────

    def detect_conflict(self, lb_id, protocol, port):
        """检查目标实例是否已有相同协议+端口的监听器

        Returns:
            {
                'has_conflict': True/False,
                'existing_listener': {...} or None,
            }
        """
        try:
            listeners = self.describe_listeners(lb_id)
            protocol_upper = protocol.upper()

            for ls in listeners:
                if ls['Protocol'].upper() == protocol_upper and ls['Port'] == int(port):
                    logger.warning(f'冲突检测: lb={lb_id} 已有 {protocol_upper}:{port} '
                                   f'(listener={ls["ListenerId"]})')
                    return {
                        'has_conflict': True,
                        'existing_listener': ls,
                    }

            return {'has_conflict': False, 'existing_listener': None}

        except Exception as e:
            logger.error(f'冲突检测异常: {e}')
            # 冲突检测失败不阻塞，返回未知状态
            return {
                'has_conflict': None,
                'existing_listener': None,
                'error': str(e),
            }
