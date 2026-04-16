"""迁移执行路由 — 创建任务、启动执行、轮询进度、确认/跳过"""
import logging
import uuid
import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session, current_app

from app.extensions import db
from app.models.migration_task import MigrationTask
from app.models.plan_item import MigrationPlanItem
from app.models.execution_log import ExecutionLog
from app.services.migration.engine import MigrationEngine

logger = logging.getLogger(__name__)

migration_bp = Blueprint('migration', __name__)


# ─── 3.1 创建迁移任务 ──────────────────────────────────────────

@migration_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建迁移任务 + plan_items

    请求体: {
        instanceMappings: [{sourceId, targetId, sourceName, targetName}],
        planItems: [{operation_type, operation_desc, target_instance_id, request_params, mapping_id}],
        failureMode: 'pause'|'continue',
        sourceRegion: 'cn-guangzhou',
        targetRegion: 'ap-guangzhou',
    }
    """
    data = request.get_json() or {}
    plan_items = data.get('planItems', [])
    if not plan_items:
        return jsonify(success=False, message='无迁移项'), 400

    fail_mode = data.get('failureMode', 'pause')
    source_region = data.get('sourceRegion', session.get('aliyun_region', ''))
    target_region = data.get('targetRegion', session.get('tencent_region', ''))

    try:
        # 创建任务主记录
        task = MigrationTask(
            task_no=f'MIG-{uuid.uuid4().hex[:8].upper()}',
            task_name=data.get('taskName', ''),
            status='draft',
            current_step='execute',
            failure_mode=fail_mode,
            source_region=source_region,
            target_region=target_region,
            total_items=len(plan_items),
        )
        db.session.add(task)
        db.session.flush()

        # 创建 plan_items
        for seq, item in enumerate(plan_items, 1):
            plan_item = MigrationPlanItem(
                task_id=task.id,
                mapping_id=item.get('mapping_id', 0),
                seq_no=seq,
                operation_type=item['operation_type'],
                operation_desc=item.get('operation_desc', ''),
                target_instance_id=item.get('target_instance_id', ''),
                request_params=item.get('request_params', {}),
                status='pending',
            )
            db.session.add(plan_item)

        db.session.commit()
        logger.info(f'迁移任务创建: id={task.id}, task_no={task.task_no}, '
                    f'items={len(plan_items)}')

        return jsonify(success=True, data={
            'task_id': task.id,
            'task_no': task.task_no,
            'total_items': len(plan_items),
        }, message='任务创建成功'), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'创建任务失败: {e}', exc_info=True)
        return jsonify(success=False, message=f'创建失败: {str(e)}'), 500


# ─── 3.2 启动执行 ──────────────────────────────────────────────

@migration_bp.route('/tasks/<int:task_id>/execute', methods=['POST'])
def execute_migration(task_id):
    """启动迁移执行（后台线程）

    请求体（可选）: { auto_confirm: true/false }
    auto_confirm=true 时跳过逐项确认弹窗，直接执行。
    """
    task = db.session.get(MigrationTask, task_id)
    if not task:
        return jsonify(success=False, message='任务不存在'), 404

    if task.status not in ('draft', 'ready', 'paused'):
        return jsonify(success=False,
                       message=f'任务状态 {task.status} 不允许执行'), 400

    # 获取腾讯云凭证
    tc_sid = session.get('tencent_sid')
    tc_sk = session.get('tencent_sk')
    if not tc_sid or not tc_sk:
        return jsonify(success=False, message='缺少腾讯云凭证'), 401

    data = request.get_json(silent=True) or {}
    auto_confirm = data.get('auto_confirm', False)

    region = task.target_region or session.get('tencent_region', 'ap-guangzhou')

    # 在后台线程启动执行引擎
    app = current_app._get_current_object()
    engine = MigrationEngine(app, tc_sid, tc_sk, region)

    def run_in_thread():
        engine.execute(task_id, auto_confirm=auto_confirm)

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    logger.info(f'迁移启动: task_id={task_id}, thread={thread.name}')
    return jsonify(success=True, data={'task_id': task_id},
                   message='迁移已启动')


# ─── 3.3 轮询进度 ──────────────────────────────────────────────

@migration_bp.route('/tasks/<int:task_id>/progress', methods=['GET'])
def get_progress(task_id):
    """轮询执行进度 — 返回当前状态、待确认项、最近日志"""
    task = db.session.get(MigrationTask, task_id)
    if not task:
        return jsonify(success=False, message='任务不存在'), 404

    # 查询所有 plan_items
    items = (db.session.query(MigrationPlanItem)
             .filter_by(task_id=task_id)
             .order_by(MigrationPlanItem.seq_no)
             .all())

    # 找到当前正在处理的项
    current_item = None
    pending_confirm = None
    for item in items:
        if item.status == 'waiting_confirm':
            pending_confirm = {
                'item_id': item.id,
                'seq_no': item.seq_no,
                'operation_type': item.operation_type,
                'operation_desc': item.operation_desc,
                'target_instance_id': item.target_instance_id,
                'request_params': item.request_params,
                'has_conflict': item.has_conflict,
                'conflict_detail': item.conflict_detail,
            }
            current_item = item
            break
        elif item.status == 'running':
            current_item = item
            break

    # 查询最近 20 条日志
    logs = (db.session.query(ExecutionLog)
            .filter_by(task_id=task_id)
            .order_by(ExecutionLog.logged_at.desc())
            .limit(20)
            .all())

    log_entries = [{
        'level': log.log_level,
        'type': log.log_type,
        'message': log.message,
        'time': log.logged_at.isoformat() if log.logged_at else '',
    } for log in reversed(logs)]

    # 构建 items 简要列表
    item_list = [{
        'id': i.id,
        'seq_no': i.seq_no,
        'operation_type': i.operation_type,
        'operation_desc': i.operation_desc,
        'status': i.status,
        'error_message': i.error_message,
    } for i in items]

    return jsonify(success=True, data={
        'task_id': task_id,
        'status': task.status,
        'progress': float(task.progress),
        'total_items': task.total_items,
        'success_count': task.success_count,
        'failed_count': task.failed_count,
        'skipped_count': task.skipped_count,
        'current_seq': current_item.seq_no if current_item else 0,
        'pending_confirm': pending_confirm,
        'items': item_list,
        'logs': log_entries,
    })


# ─── 3.4 确认/跳过 ─────────────────────────────────────────────

@migration_bp.route('/tasks/<int:task_id>/confirm', methods=['POST'])
def confirm_item(task_id):
    """确认或跳过当前待确认项

    请求体: { item_id: 123, action: 'confirm'|'skip' }
    """
    data = request.get_json() or {}
    item_id = data.get('item_id')
    action = data.get('action', 'confirm')

    if not item_id:
        return jsonify(success=False, message='缺少 item_id'), 400

    item = db.session.get(MigrationPlanItem, item_id)
    if not item or item.task_id != task_id:
        return jsonify(success=False, message='项目不存在'), 404

    if item.status != 'waiting_confirm':
        return jsonify(success=False,
                       message=f'当前状态 {item.status} 不可确认'), 400

    now = datetime.now(timezone.utc)

    if action == 'confirm':
        item.status = 'confirmed'
        item.user_confirmed = True
        item.confirmed_at = now
        msg = '已确认'
    elif action == 'skip':
        item.status = 'skipped'
        item.confirmed_at = now
        item.completed_at = now
        msg = '已跳过'
    else:
        return jsonify(success=False, message=f'无效操作: {action}'), 400

    db.session.commit()

    # 写日志
    log = ExecutionLog(
        task_id=task_id, plan_item_id=item_id,
        log_level='info', log_type='user_action',
        message=f'用户操作: {msg} [{item.operation_desc}]',
        logged_at=now,
    )
    db.session.add(log)
    db.session.commit()

    logger.info(f'确认操作: task={task_id}, item={item_id}, action={action}')
    return jsonify(success=True, message=msg)


# ─── 3.5 批量确认 ──────────────────────────────────────────────

@migration_bp.route('/tasks/<int:task_id>/batch-confirm', methods=['POST'])
def batch_confirm(task_id):
    """批量确认同类 waiting_confirm 项

    请求体: { action: 'confirm'|'skip', operation_type: 'create_listener' (可选) }
    """
    data = request.get_json() or {}
    action = data.get('action', 'confirm')
    op_type = data.get('operation_type')

    query = (db.session.query(MigrationPlanItem)
             .filter_by(task_id=task_id, status='waiting_confirm'))

    if op_type:
        query = query.filter_by(operation_type=op_type)

    items = query.all()
    if not items:
        return jsonify(success=True, data={'count': 0},
                       message='无待确认项')

    now = datetime.now(timezone.utc)
    for item in items:
        if action == 'confirm':
            item.status = 'confirmed'
            item.user_confirmed = True
            item.confirmed_at = now
        elif action == 'skip':
            item.status = 'skipped'
            item.confirmed_at = now
            item.completed_at = now

    db.session.commit()

    # 写日志
    log = ExecutionLog(
        task_id=task_id,
        log_level='info', log_type='user_action',
        message=f'批量操作: {action} {len(items)} 项'
                + (f' (类型={op_type})' if op_type else ''),
        logged_at=now,
    )
    db.session.add(log)
    db.session.commit()

    logger.info(f'批量确认: task={task_id}, action={action}, count={len(items)}')
    return jsonify(success=True, data={'count': len(items)},
                   message=f'已{action} {len(items)} 项')


# ─── 暂停/继续 ──────────────────────────────────────────────────

@migration_bp.route('/tasks/<int:task_id>/pause', methods=['POST'])
def pause_migration(task_id):
    """暂停迁移"""
    task = db.session.get(MigrationTask, task_id)
    if not task:
        return jsonify(success=False, message='任务不存在'), 404
    task.status = 'paused'
    db.session.commit()
    return jsonify(success=True, message='迁移已暂停')


@migration_bp.route('/tasks/<int:task_id>/resume', methods=['POST'])
def resume_migration(task_id):
    """继续迁移"""
    task = db.session.get(MigrationTask, task_id)
    if not task:
        return jsonify(success=False, message='任务不存在'), 404
    task.status = 'running'
    db.session.commit()
    return jsonify(success=True, message='迁移已继续')


# ─── 辅助路由（保留原有）────────────────────────────────────────

@migration_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """获取迁移任务列表"""
    tasks = (db.session.query(MigrationTask)
             .filter_by(is_deleted=False)
             .order_by(MigrationTask.created_at.desc())
             .limit(20)
             .all())
    return jsonify(success=True, data={
        'tasks': [t.to_dict() for t in tasks],
        'total': len(tasks),
    })


@migration_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取迁移任务详情"""
    task = db.session.get(MigrationTask, task_id)
    if not task:
        return jsonify(success=False, message='任务不存在'), 404
    return jsonify(success=True, data=task.to_dict())


@migration_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """软删除迁移任务"""
    task = db.session.get(MigrationTask, task_id)
    if not task:
        return jsonify(success=False, message='任务不存在'), 404
    task.is_deleted = True
    db.session.commit()
    return jsonify(success=True, message='任务已删除')


@migration_bp.route('/tasks/<int:task_id>/logs', methods=['GET'])
def get_logs(task_id):
    """获取执行日志"""
    logs = (db.session.query(ExecutionLog)
            .filter_by(task_id=task_id)
            .order_by(ExecutionLog.logged_at.desc())
            .limit(100)
            .all())
    return jsonify(success=True, data={'logs': [{
        'id': l.id,
        'level': l.log_level,
        'type': l.log_type,
        'message': l.message,
        'time': l.logged_at.isoformat() if l.logged_at else '',
    } for l in reversed(logs)]})
