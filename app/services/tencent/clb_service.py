"""腾讯云 CLB 服务封装"""
import logging
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models as clb_models

logger = logging.getLogger(__name__)


class TencentClbService:
    """腾讯云 CLB 服务"""

    MAINLAND_REGIONS = [
        {'id': 'ap-guangzhou', 'name': '华南地区（广州）'},
        {'id': 'ap-shenzhen', 'name': '华南地区（深圳）'},
        {'id': 'ap-nanjing', 'name': '华东地区（南京）'},
        {'id': 'ap-shanghai', 'name': '华东地区（上海）'},
        {'id': 'ap-beijing', 'name': '华北地区（北京）'},
        {'id': 'ap-tianjin', 'name': '华北地区（天津）'},
        {'id': 'ap-chengdu', 'name': '西南地区（成都）'},
        {'id': 'ap-chongqing', 'name': '西南地区（重庆）'},
    ]

    def __init__(self, secret_id, secret_key, region='ap-guangzhou'):
        self._cred = credential.Credential(secret_id, secret_key)
        self._region = region
        self._client = clb_client.ClbClient(self._cred, region)

    def verify_credentials(self):
        """验证凭证有效性 — 调用 DescribeLoadBalancers 测试连接"""
        try:
            req = clb_models.DescribeLoadBalancersRequest()
            req.Limit = 1
            response = self._client.DescribeLoadBalancers(req)
            result = json.loads(response.to_json_string())
            total = result.get('TotalCount', 0)
            logger.info(f'腾讯云凭证验证成功，CLB 实例总数: {total}')
            return {
                'verified': True,
                'total_count': total,
            }
        except TencentCloudSDKException as e:
            logger.warning(f'腾讯云凭证验证失败: {e.code} - {e.message}')
            if 'AuthFailure' in e.code:
                raise ValueError('SecretId 或 SecretKey 无效')
            elif 'UnauthorizedOperation' in e.code:
                raise ValueError('权限不足，请确认账号拥有 CLB 访问权限')
            else:
                raise ValueError(f'验证失败: {e.message}')

    def list_load_balancers(self, region=None):
        """获取 CLB 实例列表"""
        if region and region != self._region:
            client = clb_client.ClbClient(self._cred, region)
        else:
            client = self._client

        try:
            req = clb_models.DescribeLoadBalancersRequest()
            req.Limit = 100
            response = client.DescribeLoadBalancers(req)
            result = json.loads(response.to_json_string())
            instances = result.get('LoadBalancerSet', [])
            logger.info(f'腾讯云 CLB 实例列表查询成功，地域: {region or self._region}，数量: {len(instances)}')
            return [{
                'instance_id': lb.get('LoadBalancerId', ''),
                'instance_name': lb.get('LoadBalancerName', ''),
                'status': str(lb.get('Status', '')),
                'vip': (lb.get('LoadBalancerVips', []) or [''])[0],
                'load_balancer_type': lb.get('LoadBalancerType', ''),
                'vpc_id': lb.get('VpcId', ''),
                'subnet_id': lb.get('SubnetId', ''),
                'project_id': lb.get('ProjectId', 0),
                'create_time': lb.get('CreateTime', ''),
            } for lb in instances]
        except TencentCloudSDKException as e:
            logger.error(f'获取腾讯云 CLB 实例列表失败: {e}')
            raise ValueError(f'获取实例列表失败: {e.message}')

    @classmethod
    def get_mainland_regions(cls):
        """获取中国大陆地域列表（静态）"""
        return cls.MAINLAND_REGIONS
