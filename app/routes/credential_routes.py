"""凭证管理路由"""
import os
import logging
from flask import Blueprint, request, jsonify, session

logger = logging.getLogger(__name__)

credential_bp = Blueprint('credential', __name__)


@credential_bp.route('/aliyun/verify', methods=['POST'])
def verify_aliyun():
    """验证阿里云凭证 — 调用 SLB DescribeRegions"""
    data = request.get_json()
    ak = data.get('access_key_id', '').strip() if data else ''
    sk = data.get('access_key_secret', '').strip() if data else ''

    if not ak or not sk:
        return jsonify(success=False, error='INVALID_PARAMS', message='请提供 AccessKey ID 和 Secret'), 400

    try:
        from app.services.aliyun.slb_service import AliyunSlbService
        service = AliyunSlbService(ak, sk)
        result = service.verify_credentials()

        session['aliyun_ak'] = ak
        session['aliyun_sk'] = sk
        session.permanent = True

        logger.info('阿里云凭证验证成功')
        return jsonify(success=True, data=result, message='阿里云凭证验证成功')
    except ValueError as e:
        logger.warning(f'阿里云凭证验证失败: {e}')
        return jsonify(success=False, error='VERIFY_FAILED', message=str(e)), 401
    except Exception as e:
        logger.error(f'阿里云凭证验证异常: {e}', exc_info=True)
        return jsonify(success=False, error='INTERNAL_ERROR', message='验证服务异常，请稍后重试'), 500


@credential_bp.route('/tencent/verify', methods=['POST'])
def verify_tencent():
    """验证腾讯云凭证 — 调用 CLB DescribeLoadBalancers"""
    data = request.get_json()
    sid = data.get('secret_id', '').strip() if data else ''
    sk = data.get('secret_key', '').strip() if data else ''

    if not sid or not sk:
        return jsonify(success=False, error='INVALID_PARAMS', message='请提供 SecretId 和 SecretKey'), 400

    try:
        from app.services.tencent.clb_service import TencentClbService
        service = TencentClbService(sid, sk)
        result = service.verify_credentials()

        session['tencent_sid'] = sid
        session['tencent_sk'] = sk
        session.permanent = True

        logger.info('腾讯云凭证验证成功')
        return jsonify(success=True, data=result, message='腾讯云凭证验证成功')
    except ValueError as e:
        logger.warning(f'腾讯云凭证验证失败: {e}')
        return jsonify(success=False, error='VERIFY_FAILED', message=str(e)), 401
    except Exception as e:
        logger.error(f'腾讯云凭证验证异常: {e}', exc_info=True)
        return jsonify(success=False, error='INTERNAL_ERROR', message='验证服务异常，请稍后重试'), 500


@credential_bp.route('/status', methods=['GET'])
def credential_status():
    """获取凭证状态（含 .env 预配置检测）"""
    env_aliyun = bool(os.getenv('ALIYUN_ACCESS_KEY_ID'))
    env_tencent = bool(os.getenv('TENCENT_SECRET_ID'))

    return jsonify(success=True, data={
        'aliyun_configured': bool(session.get('aliyun_ak')),
        'tencent_configured': bool(session.get('tencent_sid')),
        'env_aliyun_available': env_aliyun,
        'env_tencent_available': env_tencent,
    })


@credential_bp.route('/load-env', methods=['POST'])
def load_from_env():
    """从 .env 文件加载预配置凭证到会话"""
    loaded = {}

    aliyun_ak = os.getenv('ALIYUN_ACCESS_KEY_ID', '').strip()
    aliyun_sk = os.getenv('ALIYUN_ACCESS_KEY_SECRET', '').strip()
    if aliyun_ak and aliyun_sk:
        session['aliyun_ak'] = aliyun_ak
        session['aliyun_sk'] = aliyun_sk
        loaded['aliyun'] = True
        logger.info('从 .env 加载阿里云凭证')

    tencent_sid = os.getenv('TENCENT_SECRET_ID', '').strip()
    tencent_sk = os.getenv('TENCENT_SECRET_KEY', '').strip()
    if tencent_sid and tencent_sk:
        session['tencent_sid'] = tencent_sid
        session['tencent_sk'] = tencent_sk
        loaded['tencent'] = True
        logger.info('从 .env 加载腾讯云凭证')

    if loaded:
        session.permanent = True

    # 单用户内部工具：返回凭证值供前端填充输入框
    return jsonify(success=True, data={
        'loaded': loaded,
        'aliyun_ak': aliyun_ak if loaded.get('aliyun') else '',
        'aliyun_sk': aliyun_sk if loaded.get('aliyun') else '',
        'tencent_sid': tencent_sid if loaded.get('tencent') else '',
        'tencent_sk': tencent_sk if loaded.get('tencent') else '',
        'aliyun_region': os.getenv('ALIYUN_REGION', ''),
        'tencent_region': os.getenv('TENCENT_REGION', ''),
    }, message=f'已加载 {len(loaded)} 组凭证')


@credential_bp.route('/save-env', methods=['POST'])
def save_to_env():
    """将当前会话凭证保存到 .env 文件"""
    data = request.get_json() or {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')

    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()

    env_vars = {}
    if session.get('aliyun_ak'):
        env_vars['ALIYUN_ACCESS_KEY_ID'] = session['aliyun_ak']
        env_vars['ALIYUN_ACCESS_KEY_SECRET'] = session['aliyun_sk']
    if data.get('aliyun_region'):
        env_vars['ALIYUN_REGION'] = data['aliyun_region']
    if session.get('tencent_sid'):
        env_vars['TENCENT_SECRET_ID'] = session['tencent_sid']
        env_vars['TENCENT_SECRET_KEY'] = session['tencent_sk']
    if data.get('tencent_region'):
        env_vars['TENCENT_REGION'] = data['tencent_region']

    # 更新已有行或追加
    updated_keys = set()
    new_lines = []
    for line in lines:
        key = line.split('=')[0].strip() if '=' in line else ''
        if key in env_vars:
            new_lines.append(f'{key}={env_vars[key]}\n')
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in env_vars.items():
        if key not in updated_keys:
            new_lines.append(f'{key}={value}\n')

    with open(env_path, 'w') as f:
        f.writelines(new_lines)

    logger.info(f'凭证已保存到 .env，更新 {len(env_vars)} 个变量')
    return jsonify(success=True, message=f'已保存 {len(env_vars)} 个配置到 .env 文件')
