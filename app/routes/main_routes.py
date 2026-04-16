"""主页路由"""
import os
from flask import Blueprint, send_from_directory, jsonify

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """主页 — 返回前端 SPA"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'public')
    return send_from_directory(static_dir, 'index.html')


@main_bp.route('/api/health')
def health():
    """健康检查"""
    return jsonify(success=True, data={'status': 'ok'}, message='服务运行正常')
