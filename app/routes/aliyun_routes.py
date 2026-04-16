"""阿里云 CLB 读取路由（全程只读）"""
import logging
from flask import Blueprint, jsonify, session, request

from app.services.aliyun.slb_service import AliyunSlbService

logger = logging.getLogger(__name__)

aliyun_bp = Blueprint('aliyun', __name__)


def _get_service():
    """从会话获取阿里云服务实例"""
    ak = session.get('aliyun_ak')
    sk = session.get('aliyun_sk')
    if not ak or not sk:
        return None
    region = request.args.get('region', 'cn-hangzhou')
    return AliyunSlbService(ak, sk, region)


@aliyun_bp.route('/regions', methods=['GET'])
def list_regions():
    """获取阿里云中国大陆地域列表"""
    return jsonify(success=True, data={'regions': AliyunSlbService.get_mainland_regions()})


@aliyun_bp.route('/clb/instances', methods=['GET'])
def list_instances():
    """获取阿里云 CLB 实例列表"""
    service = _get_service()
    if not service:
        return jsonify(success=False, error='NO_CREDENTIAL', message='请先配置阿里云凭证'), 401

    region = request.args.get('region', '')
    try:
        instances = service.list_load_balancers(region_id=region or None)
        return jsonify(success=True, data={'instances': instances, 'total': len(instances)})
    except ValueError as e:
        return jsonify(success=False, error='API_ERROR', message=str(e)), 500


@aliyun_bp.route('/clb/instances/<instance_id>/config', methods=['GET'])
def get_instance_config(instance_id):
    """获取阿里云 CLB 实例完整配置（监听器+转发规则+健康检查+高级参数+ACL）"""
    service = _get_service()
    if not service:
        return jsonify(success=False, error='NO_CREDENTIAL', message='请先配置阿里云凭证'), 401

    region = request.args.get('region', '')
    try:
        config = service.get_full_config(instance_id, region_id=region or None)
        return jsonify(success=True, data=config)
    except ValueError as e:
        return jsonify(success=False, error='API_ERROR', message=str(e)), 500


@aliyun_bp.route('/clb/instances/<instance_id>/listeners', methods=['GET'])
def list_listeners(instance_id):
    """获取监听器列表"""
    service = _get_service()
    if not service:
        return jsonify(success=False, error='NO_CREDENTIAL', message='请先配置阿里云凭证'), 401

    region = request.args.get('region', '')
    try:
        listeners = service.list_listeners(instance_id, region_id=region or None)
        return jsonify(success=True, data={'listeners': listeners})
    except ValueError as e:
        return jsonify(success=False, error='API_ERROR', message=str(e)), 500


@aliyun_bp.route('/clb/instances/<instance_id>/rules', methods=['GET'])
def list_rules(instance_id):
    """获取 HTTP/HTTPS 转发规则"""
    service = _get_service()
    if not service:
        return jsonify(success=False, error='NO_CREDENTIAL', message='请先配置阿里云凭证'), 401

    port = request.args.get('port', type=int)
    region = request.args.get('region', '')
    if not port:
        return jsonify(success=False, error='INVALID_PARAMS', message='请提供 port 参数'), 400

    try:
        rules = service.list_forwarding_rules(instance_id, port, region_id=region or None)
        return jsonify(success=True, data={'rules': rules})
    except ValueError as e:
        return jsonify(success=False, error='API_ERROR', message=str(e)), 500
