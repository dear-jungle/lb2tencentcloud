"""腾讯云 CLB 读写路由"""
import logging
from flask import Blueprint, jsonify, request, session
from app.services.tencent.clb_service import TencentClbService

logger = logging.getLogger(__name__)

tencent_bp = Blueprint('tencent', __name__)


@tencent_bp.route('/regions', methods=['GET'])
def list_regions():
    """获取腾讯云中国大陆地域列表"""
    regions = [
        {'id': 'ap-guangzhou', 'name': '华南地区（广州）'},
        {'id': 'ap-shenzhen', 'name': '华南地区（深圳）'},
        {'id': 'ap-nanjing', 'name': '华东地区（南京）'},
        {'id': 'ap-shanghai', 'name': '华东地区（上海）'},
        {'id': 'ap-beijing', 'name': '华北地区（北京）'},
        {'id': 'ap-tianjin', 'name': '华北地区（天津）'},
        {'id': 'ap-chengdu', 'name': '西南地区（成都）'},
        {'id': 'ap-chongqing', 'name': '西南地区（重庆）'},
    ]
    return jsonify(success=True, data={'regions': regions})


@tencent_bp.route('/clb/instances', methods=['GET'])
def list_instances():
    """获取腾讯云 CLB 实例列表（ID + 名称）"""
    if not session.get('tencent_sid'):
        return jsonify(success=False, error='NO_CREDENTIAL', message='请先配置腾讯云凭证'), 401
    region = request.args.get('region', session.get('tencent_region', 'ap-guangzhou'))
    try:
        svc = TencentClbService(session['tencent_sid'], session['tencent_sk'], region)
        instances = svc.list_load_balancers(region)
        # 返回简化格式：instance_id + instance_name
        result = [{'instance_id': i['instance_id'], 'instance_name': i['instance_name'],
                   'vip': i.get('vip', ''), 'load_balancer_type': i.get('load_balancer_type', '')}
                  for i in instances]
        logger.info(f'腾讯云 {region} CLB 实例: {len(result)} 个')
        return jsonify(success=True, data={'instances': result})
    except Exception as e:
        logger.error(f'获取腾讯云 CLB 实例列表失败: {e}')
        return jsonify(success=False, message=str(e)), 500


@tencent_bp.route('/vpc/list', methods=['GET'])
def list_vpcs():
    """获取腾讯云 VPC 列表（供创建实例使用）"""
    if not session.get('tencent_sid'):
        return jsonify(success=False, error='NO_CREDENTIAL', message='请先配置腾讯云凭证'), 401
    # TODO: 调用腾讯云 VPC SDK
    return jsonify(success=True, data={'vpcs': []})
