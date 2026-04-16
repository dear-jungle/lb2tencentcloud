"""阿里云 SLB 服务封装（只读）"""
import json
import logging
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkslb.request.v20140515.DescribeRegionsRequest import DescribeRegionsRequest
from aliyunsdkslb.request.v20140515.DescribeLoadBalancersRequest import DescribeLoadBalancersRequest
from aliyunsdkslb.request.v20140515.DescribeLoadBalancerAttributeRequest import DescribeLoadBalancerAttributeRequest
from aliyunsdkslb.request.v20140515.DescribeLoadBalancerListenersRequest import DescribeLoadBalancerListenersRequest
from aliyunsdkslb.request.v20140515.DescribeHealthStatusRequest import DescribeHealthStatusRequest
from aliyunsdkslb.request.v20140515.DescribeRulesRequest import DescribeRulesRequest
from aliyunsdkslb.request.v20140515.DescribeAccessControlListsRequest import DescribeAccessControlListsRequest
from aliyunsdkslb.request.v20140515.DescribeAccessControlListAttributeRequest import DescribeAccessControlListAttributeRequest

logger = logging.getLogger(__name__)


class AliyunSlbService:
    """阿里云 SLB 只读服务 — 严禁调用任何写入 API"""

    MAINLAND_REGIONS = [
        {'id': 'cn-hangzhou', 'name': '华东1（杭州）'},
        {'id': 'cn-shanghai', 'name': '华东2（上海）'},
        {'id': 'cn-nanjing', 'name': '华东5（南京）'},
        {'id': 'cn-qingdao', 'name': '华北1（青岛）'},
        {'id': 'cn-beijing', 'name': '华北2（北京）'},
        {'id': 'cn-zhangjiakou', 'name': '华北3（张家口）'},
        {'id': 'cn-huhehaote', 'name': '华北5（呼和浩特）'},
        {'id': 'cn-wulanchabu', 'name': '华北6（乌兰察布）'},
        {'id': 'cn-shenzhen', 'name': '华南1（深圳）'},
        {'id': 'cn-heyuan', 'name': '华南2（河源）'},
        {'id': 'cn-guangzhou', 'name': '华南3（广州）'},
        {'id': 'cn-chengdu', 'name': '西南1（成都）'},
    ]

    def __init__(self, access_key_id, access_key_secret, region_id='cn-hangzhou'):
        self._ak = access_key_id
        self._sk = access_key_secret
        self._region_id = region_id
        self._client = AcsClient(access_key_id, access_key_secret, region_id)

    def _get_client(self, region_id=None):
        if region_id and region_id != self._region_id:
            return AcsClient(self._ak, self._sk, region_id)
        return self._client

    def _do_request(self, req, region_id=None):
        req.set_accept_format('json')
        client = self._get_client(region_id)
        response = client.do_action_with_exception(req)
        return json.loads(response)

    def verify_credentials(self):
        """验证凭证有效性 — 调用 DescribeRegions"""
        try:
            result = self._do_request(DescribeRegionsRequest())
            regions = result.get('Regions', {}).get('Region', [])
            logger.info(f'阿里云凭证验证成功，可用地域数: {len(regions)}')
            return {'verified': True, 'region_count': len(regions)}
        except ClientException as e:
            logger.warning(f'阿里云凭证验证失败: {e.error_code}')
            raise ValueError(f'凭证验证失败: {e.message}')
        except ServerException as e:
            if 'InvalidAccessKeyId' in e.error_code:
                raise ValueError('AccessKey ID 无效')
            elif 'SignatureDoesNotMatch' in e.error_code:
                raise ValueError('AccessKey Secret 不正确')
            raise ValueError(f'验证失败: {e.message}')

    def list_load_balancers(self, region_id=None):
        """获取 CLB 实例列表（只读）"""
        region = region_id or self._region_id
        req = DescribeLoadBalancersRequest()
        req.set_PageSize(100)
        try:
            result = self._do_request(req, region)
            instances = result.get('LoadBalancers', {}).get('LoadBalancer', [])
            logger.info(f'查询 CLB 实例: 地域={region}, 数量={len(instances)}')
            return [{
                'instance_id': lb.get('LoadBalancerId', ''),
                'instance_name': lb.get('LoadBalancerName', ''),
                'status': lb.get('LoadBalancerStatus', ''),
                'address': lb.get('Address', ''),
                'address_type': lb.get('AddressType', ''),
                'network_type': lb.get('NetworkType', ''),
                'vpc_id': lb.get('VpcId', ''),
                'create_time': lb.get('CreateTime', ''),
            } for lb in instances]
        except (ClientException, ServerException) as e:
            raise ValueError(f'获取实例列表失败: {e.message}')

    def get_instance_detail(self, load_balancer_id, region_id=None):
        """获取 CLB 实例详情（只读）"""
        req = DescribeLoadBalancerAttributeRequest()
        req.set_LoadBalancerId(load_balancer_id)
        try:
            return self._do_request(req, region_id)
        except (ClientException, ServerException) as e:
            raise ValueError(f'获取实例详情失败: {e.message}')

    def list_listeners(self, load_balancer_id, region_id=None):
        """获取监听器列表（只读）— 包含协议、端口、调度算法等"""
        req = DescribeLoadBalancerListenersRequest()
        req.set_query_params({'LoadBalancerId.1': load_balancer_id, 'MaxResults': 100})
        try:
            result = self._do_request(req, region_id)
            listeners = result.get('Listeners', [])
            logger.info(f'查询监听器: {load_balancer_id}, 数量={len(listeners)}')
            return [{
                'listener_port': l.get('ListenerPort'),
                'listener_protocol': l.get('ListenerProtocol', '').lower(),
                'backend_port': l.get('BackendServerPort'),
                'scheduler': l.get('Scheduler', ''),
                'status': l.get('Status', ''),
                'bandwidth': l.get('Bandwidth', -1),
                'description': l.get('Description', ''),
                'connection_timeout': l.get('ConnectionDrainTimeout'),
                'idle_timeout': l.get('IdleTimeout'),
                'request_timeout': l.get('RequestTimeout'),
                'sticky_session': l.get('StickySession', 'off'),
                'sticky_session_type': l.get('StickySessionType'),
                'cookie_timeout': l.get('CookieTimeout'),
                'cookie': l.get('Cookie'),
                'health_check': l.get('HealthCheck', 'off'),
                'health_check_type': l.get('HealthCheckType'),
                'health_check_domain': l.get('HealthCheckDomain'),
                'health_check_uri': l.get('HealthCheckURI'),
                'health_check_connect_port': l.get('HealthCheckConnectPort'),
                'healthy_threshold': l.get('HealthyThreshold'),
                'unhealthy_threshold': l.get('UnhealthyThreshold'),
                'health_check_timeout': l.get('HealthCheckTimeout'),
                'health_check_interval': l.get('HealthCheckInterval'),
                'health_check_http_code': l.get('HealthCheckHttpCode'),
                'acl_status': l.get('AclStatus', 'off'),
                'acl_type': l.get('AclType'),
                'acl_id': l.get('AclId'),
                'raw': l,
            } for l in listeners]
        except (ClientException, ServerException) as e:
            raise ValueError(f'获取监听器列表失败: {e.message}')

    def list_forwarding_rules(self, load_balancer_id, listener_port, region_id=None):
        """获取 HTTP/HTTPS 转发规则（只读）"""
        req = DescribeRulesRequest()
        req.set_LoadBalancerId(load_balancer_id)
        req.set_ListenerPort(listener_port)
        try:
            result = self._do_request(req, region_id)
            rules = result.get('Rules', {}).get('Rule', [])
            logger.info(f'查询转发规则: {load_balancer_id}:{listener_port}, 数量={len(rules)}')
            return [{
                'rule_id': r.get('RuleId', ''),
                'rule_name': r.get('RuleName', ''),
                'domain': r.get('Domain', ''),
                'url': r.get('Url', ''),
                'vserver_group_id': r.get('VServerGroupId', ''),
                'raw': r,
            } for r in rules]
        except (ClientException, ServerException) as e:
            raise ValueError(f'获取转发规则失败: {e.message}')

    def list_acl_lists(self, region_id=None):
        """获取访问控制列表（只读）"""
        req = DescribeAccessControlListsRequest()
        try:
            result = self._do_request(req, region_id)
            acls = result.get('Acls', {}).get('Acl', [])
            return [{
                'acl_id': a.get('AclId', ''),
                'acl_name': a.get('AclName', ''),
            } for a in acls]
        except (ClientException, ServerException) as e:
            raise ValueError(f'获取 ACL 列表失败: {e.message}')

    def get_acl_detail(self, acl_id, region_id=None):
        """获取 ACL 详情（只读）"""
        req = DescribeAccessControlListAttributeRequest()
        req.set_AclId(acl_id)
        try:
            result = self._do_request(req, region_id)
            entries = result.get('AclEntrys', {}).get('AclEntry', [])
            return {
                'acl_id': result.get('AclId', ''),
                'acl_name': result.get('AclName', ''),
                'entries': [{'cidr': e.get('AclEntryIP', ''), 'comment': e.get('AclEntryComment', '')} for e in entries],
            }
        except (ClientException, ServerException) as e:
            raise ValueError(f'获取 ACL 详情失败: {e.message}')

    def get_full_config(self, load_balancer_id, region_id=None):
        """获取 CLB 实例完整配置（只读聚合）"""
        detail = self.get_instance_detail(load_balancer_id, region_id)
        listeners = self.list_listeners(load_balancer_id, region_id)

        for listener in listeners:
            proto = listener.get('listener_protocol', '')
            port = listener.get('listener_port')
            if proto in ('http', 'https') and port:
                listener['forwarding_rules'] = self.list_forwarding_rules(
                    load_balancer_id, port, region_id
                )
            else:
                listener['forwarding_rules'] = []

            if listener.get('acl_status') == 'on' and listener.get('acl_id'):
                try:
                    listener['acl_detail'] = self.get_acl_detail(listener['acl_id'], region_id)
                except ValueError:
                    listener['acl_detail'] = None

        return {
            'instance': detail,
            'listeners': listeners,
        }

    @classmethod
    def get_mainland_regions(cls):
        return cls.MAINLAND_REGIONS
