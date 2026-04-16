"""配置映射路由"""
import logging
from flask import Blueprint, jsonify, request, session, current_app
from app.services.mapper.engine import ConfigMappingEngine
from app.services.tencent.clb_writer import TencentClbWriter

logger = logging.getLogger(__name__)

mapping_bp = Blueprint('mapping', __name__)


def _get_tencent_writer():
    """从 session 获取凭证构建 Writer（复用验证时保存的凭证）"""
    sid = session.get('tencent_secret_id')
    sk = session.get('tencent_secret_key')
    region = session.get('target_region', 'ap-guangzhou')
    if not sid or not sk:
        return None
    return TencentClbWriter(sid, sk, region)


def _serialize_results(results):
    """序列化映射结果列表"""
    return [{
        'source_type': r.source_type,
        'source_description': r.source_description,
        'source_config': r.source_config,
        'target_config': r.target_config,
        'status': r.status,
        'diff_summary': r.diff_summary,
        'incompatible_items': [{
            'config_name': i.config_name,
            'source_value': i.source_value,
            'reason': i.reason,
            'severity': i.severity,
            'suggestion': i.suggestion,
            'recommendation': i.recommendation,
            'alternatives': i.alternatives,
        } for i in r.incompatible_items],
    } for r in results]


@mapping_bp.route('/tasks/<int:task_id>/execute', methods=['POST'])
def execute_mapping(task_id):
    """执行配置映射（扁平模式，向后兼容）"""
    data = request.get_json() or {}
    listeners = data.get('listeners', [])
    if not listeners:
        return jsonify(success=False, error='NO_DATA', message='无监听器数据'), 400

    engine = ConfigMappingEngine()
    results = engine.map_full_config(listeners)
    results_data = _serialize_results(results)

    return jsonify(success=True, data={
        'task_id': task_id,
        'results': results_data,
        'summary': {
            'total': len(results),
            'mapped': sum(1 for r in results if r.status == 'mapped'),
            'partial': sum(1 for r in results if r.status == 'partial'),
            'incompatible': sum(1 for r in results if r.status == 'incompatible'),
        },
    }, message='映射执行完成')


@mapping_bp.route('/execute-by-instance', methods=['POST'])
def execute_by_instance():
    """按实例分组执行映射（新接口）

    请求体: { instanceMappings: [{sourceId, targetId, sourceName, targetName, listeners}] }
    """
    data = request.get_json() or {}
    instance_mappings = data.get('instanceMappings', [])
    if not instance_mappings:
        return jsonify(success=False, error='NO_DATA', message='无实例映射数据'), 400

    engine = ConfigMappingEngine()
    grouped = engine.map_by_instance(instance_mappings)

    # 序列化
    result_data = {}
    total_summary = {'total': 0, 'mapped': 0, 'partial': 0, 'incompatible': 0}
    for source_id, group in grouped.items():
        result_data[source_id] = {
            'sourceId': group['sourceId'],
            'targetId': group['targetId'],
            'sourceName': group['sourceName'],
            'targetName': group['targetName'],
            'results': _serialize_results(group['results']),
            'summary': group['summary'],
        }
        for k in total_summary:
            total_summary[k] += group['summary'].get(k, 0)

    logger.info(f'按实例映射完成: {len(instance_mappings)} 个实例, '
                f'总计={total_summary["total"]}, 映射={total_summary["mapped"]}')

    return jsonify(success=True, data={
        'groups': result_data,
        'summary': total_summary,
    }, message='映射执行完成')


@mapping_bp.route('/tasks/<int:task_id>/results', methods=['GET'])
def get_results(task_id):
    """获取映射结果列表"""
    # TODO: 从 MySQL mapping_result 表查询持久化的结果
    return jsonify(success=True, data={'results': [], 'task_id': task_id})


@mapping_bp.route('/conflict-detect', methods=['POST'])
def detect_conflicts():
    """检测多对一映射端口冲突"""
    data = request.get_json() or {}
    all_listeners = data.get('listeners', [])

    engine = ConfigMappingEngine()
    conflicts = engine.detect_port_conflicts(all_listeners)

    return jsonify(success=True, data={
        'has_conflict': len(conflicts) > 0,
        'conflicts': conflicts,
        'count': len(conflicts),
    })


@mapping_bp.route('/detect-target-conflicts', methods=['POST'])
def detect_target_conflicts():
    """检测待迁移监听器与目标实例已有监听器的协议+端口冲突

    请求体: { targetInstanceId, listeners: [{listener_protocol, listener_port}] }
    """
    data = request.get_json() or {}
    target_instance_id = data.get('targetInstanceId', '')
    listeners = data.get('listeners', [])

    if not target_instance_id:
        return jsonify(success=False, error='MISSING_TARGET', message='缺少 targetInstanceId'), 400
    if not listeners:
        return jsonify(success=True, data={'has_conflict': False, 'conflicts': [], 'source': 'target'})

    writer = _get_tencent_writer()
    if not writer:
        return jsonify(success=False, error='NO_CREDS', message='未检测到腾讯云凭证，请先验证连接'), 401

    try:
        existing_listeners = writer.describe_listeners(target_instance_id)

        conflicts = []
        for src_listener in listeners:
            src_proto = (src_listener.get('listener_protocol') or '').upper()
            src_port = int(src_listener.get('listener_port') or 0)
            if not src_proto or not src_port:
                continue

            for exist in existing_listeners:
                exist_proto = (exist.get('Protocol') or '').upper()
                exist_port = int(exist.get('Port') or 0)
                if src_proto == exist_proto and src_port == exist_port:
                    conflicts.append({
                        'protocol': src_protocol_display(src_proto),
                        'port': src_port,
                        'source_description': src_listener.get('description', f'{src_proto}:{src_port}'),
                        'existing_listener_id': exist.get('ListenerId'),
                        'existing_name': exist.get('ListenerName', ''),
                    })

        logger.info(f'目标端冲突检测: lb={target_instance_id}, 待检={len(listeners)}, 冲突={len(conflicts)}')
        return jsonify(success=True, data={
            'has_conflict': len(conflicts) > 0,
            'conflicts': conflicts,
            'count': len(conflicts),
            'source': 'target',
        })

    except Exception as e:
        logger.error(f'目标端冲突检测失败: {e}')
        return jsonify(success=False, error='DETECT_FAILED', message=str(e)), 500


def src_protocol_display(proto):
    """协议显示名称统一化"""
    mapping = {'TCP': 'TCP', 'UDP': 'UDP', 'HTTP': 'HTTP', 'HTTPS': 'HTTPS'}
    return mapping.get(proto.upper(), proto)
