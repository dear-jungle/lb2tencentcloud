"""Flask 应用工厂"""
import os
import logging
from datetime import timedelta

from flask import Flask, jsonify
from flask_cors import CORS

from app.extensions import db, migrate


def create_app(config_name=None):
    """创建并配置 Flask 应用实例"""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'public'),
        static_url_path=''
    )

    _load_config(app, config_name)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _configure_logging(app)

    return app


def _load_config(app, config_name):
    """加载配置"""
    dev_mode = os.getenv('DEV_MODE', '1') == '1'

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'lb2tc-dev-secret-key-change-in-prod')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

    # 数据库配置
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://lb2tc:lb2tc_pass_2026@localhost:3306/lb2tencentcloud?charset=utf8mb4'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 开发模式配置
    if dev_mode:
        app.config['DEBUG'] = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

        @app.after_request
        def add_no_cache_headers(response):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

    # SQLite 不支持连接池参数
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'sqlite' not in db_uri:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
        }


def _init_extensions(app):
    """初始化 Flask 扩展"""
    db.init_app(app)
    migrate.init_app(app, db)

    # 导入所有模型，确保 Alembic 能检测到
    with app.app_context():
        from app.models import (  # noqa: F401
            MigrationTask, InstanceMapping, SourceClbSnapshot,
            SourceListener, SourceForwardingRule, SourceHealthCheck,
            SourceAclPolicy, MappingResult, IncompatibleItem,
            MigrationPlanItem, ExecutionLog, MigrationReport,
            ReportDetail, EnumMappingRule,
        )

    # CORS 配置
    dev_mode = os.getenv('DEV_MODE', '1') == '1'
    if dev_mode:
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
        CORS(app, resources={r"/api/*": {"origins": allowed_origins}})


def _register_blueprints(app):
    """注册 Blueprint 路由"""
    from app.routes.main_routes import main_bp
    from app.routes.credential_routes import credential_bp
    from app.routes.aliyun_routes import aliyun_bp
    from app.routes.tencent_routes import tencent_bp
    from app.routes.mapping_routes import mapping_bp
    from app.routes.migration_routes import migration_bp
    from app.routes.report_routes import report_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(credential_bp, url_prefix='/api/credentials')
    app.register_blueprint(aliyun_bp, url_prefix='/api/aliyun')
    app.register_blueprint(tencent_bp, url_prefix='/api/tencent')
    app.register_blueprint(mapping_bp, url_prefix='/api/mapping')
    app.register_blueprint(migration_bp, url_prefix='/api/migration')
    app.register_blueprint(report_bp, url_prefix='/api/report')


def _register_error_handlers(app):
    """注册全局异常处理"""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(success=False, error='BAD_REQUEST', message=str(e.description)), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(success=False, error='NOT_FOUND', message='资源不存在'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(success=False, error='INTERNAL_ERROR', message='服务器内部错误'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'未处理异常: {e}', exc_info=True)
        return jsonify(success=False, error='INTERNAL_ERROR', message='服务器内部错误'), 500


def _configure_logging(app):
    """配置日志"""
    log_level = os.getenv('LOG_LEVEL', 'DEBUG' if app.debug else 'INFO')

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    app.logger.addHandler(file_handler)
