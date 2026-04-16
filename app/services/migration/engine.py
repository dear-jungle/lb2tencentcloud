"""迁移执行引擎 — 逐项执行、用户确认、冲突检测、失败处理"""
import logging
import time
from datetime import datetime, timezone

from app.extensions import db
from app.models.migration_task import MigrationTask
from app.models.plan_item import MigrationPlanItem
from app.models.execution_log import ExecutionLog
from app.services.tencent.clb_writer import TencentClbWriter

logger = logging.getLogger(__name__)

# 确认等待超时（秒）
CONFIRM_TIMEOUT = 300  # 5 分钟
CONFIRM_POLL_INTERVAL = 1  # 每秒轮询一次


class MigrationEngine:
    """迁移执行引擎

    安全约束：
    - 每个写操作执行前必须经用户确认（user_confirmed=True）
    - 写操作前自动检测端口冲突
    - 所有操作实时持久化到数据库
    """

    def __init__(self, app, secret_id, secret_key, region):
        """
        Args:
            app: Flask app 实例（用于 app_context）
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            region: 目标地域
        """
        self._app = app
        self._writer = TencentClbWriter(secret_id, secret_key, region)
        self._region = region

    # ─── 2.2 准备 ────────────────────────────────────────────────

    def prepare(self, task_id, plan_items):
        """将 plan_items 写入数据库（status=pending）

        Args:
            task_id: 迁移任务 ID
            plan_items: [{
                'operation_type': 'create_listener',
                'operation_desc': '创建 TCP:80 监听器',
                'target_instance_id': 'lb-xxx',
                'request_params': {...},
                'mapping_id': 1,
            }, ...]

        Returns:
            创建的 plan_item ID 列表
        """
        with self._app.app_context():
            ids = []
            for seq, item in enumerate(plan_items, 1):
                plan_item = MigrationPlanItem(
                    task_id=task_id,
                    mapping_id=item.get('mapping_id', 0),
                    seq_no=seq,
                    operation_type=item['operation_type'],
                    operation_desc=item.get('operation_desc', ''),
                    target_instance_id=item.get('target_instance_id', ''),
                    request_params=item.get('request_params', {}),
                    status='pending',
                )
                db.session.add(plan_item)
                db.session.flush()
                ids.append(plan_item.id)

            # 更新任务总数
            task = db.session.get(MigrationTask, task_id)
            if task:
                task.total_items = len(plan_items)
                task.status = 'ready'

            db.session.commit()
            self._log(task_id, 'info', 'system', f'准备完成: {len(plan_items)} 项待执行')
            return ids

    # ─── 2.3 主循环执行 ──────────────────────────────────────────

    def execute(self, task_id, auto_confirm=False):
        """主循环执行 — 在后台线程中调用

        Args:
            task_id: 迁移任务 ID
            auto_confirm: True=跳过逐项确认直接执行, False=每步等待用户确认

        流程：遍历 pending 项 → 冲突检测 → (等待确认或自动确认) → 调 API → 保存结果
        """
        self._auto_confirm = auto_confirm

        with self._app.app_context():
            task = db.session.get(MigrationTask, task_id)
            if not task:
                logger.error(f'任务不存在: {task_id}')
                return

            task.status = 'running'
            task.started_at = datetime.now(timezone.utc)
            db.session.commit()
            mode_text = '自动执行（无逐项确认）' if auto_confirm else '逐项确认模式'
            self._log(task_id, 'info', 'system', f'迁移开始执行 — {mode_text}')

            try:
                items = (db.session.query(MigrationPlanItem)
                         .filter_by(task_id=task_id)
                         .order_by(MigrationPlanItem.seq_no)
                         .all())

                for item in items:
                    # 检查暂停标志 (2.6)
                    task = db.session.get(MigrationTask, task_id)
                    if task.status == 'paused':
                        self._log(task_id, 'info', 'system', '迁移已暂停，等待继续...')
                        self._wait_for_resume(task_id)
                        task = db.session.get(MigrationTask, task_id)
                        if task.status == 'cancelled':
                            self._log(task_id, 'info', 'system', '迁移已取消')
                            break

                    # 跳过已完成/跳过的项
                    if item.status in ('success', 'skipped', 'cancelled'):
                        continue

                    self._execute_single_item(task_id, item, task.failure_mode)

                # 执行完成，更新任务状态
                self._finalize_task(task_id)

            except Exception as e:
                logger.error(f'迁移引擎异常: {e}', exc_info=True)
                self._log(task_id, 'error', 'error', f'引擎异常: {str(e)}')
                task = db.session.get(MigrationTask, task_id)
                if task:
                    task.status = 'failed'
                    db.session.commit()

    def _execute_single_item(self, task_id, item, fail_mode):
        """执行单个 plan_item"""
        seq = item.seq_no
        desc = item.operation_desc
        self._log(task_id, 'info', 'progress',
                  f'[{seq}] 开始: {desc}', plan_item_id=item.id)

        try:
            # 1. 冲突检测
            conflict = self._detect_conflict(item)
            if conflict and conflict.get('has_conflict'):
                item.has_conflict = True
                item.conflict_detail = conflict
                db.session.commit()
                self._log(task_id, 'warn', 'api_call',
                          f'[{seq}] 冲突: {item.target_instance_id} 已有 '
                          f'{conflict["existing_listener"]["Protocol"]}:'
                          f'{conflict["existing_listener"]["Port"]}',
                          plan_item_id=item.id)

            # 2. 等待确认或自动确认
            if self._auto_confirm:
                # 自动确认模式：直接标记为 confirmed
                item.status = 'confirmed'
                item.user_confirmed = True
                item.confirmed_at = datetime.now(timezone.utc)
                db.session.commit()
                self._log(task_id, 'info', 'system',
                          f'[{seq}] 自动确认: {desc}', plan_item_id=item.id)
            else:
                # 逐项确认模式：设 waiting_confirm，等前端弹窗
                item.status = 'waiting_confirm'
                db.session.commit()
                self._log(task_id, 'info', 'confirm',
                          f'[{seq}] 等待用户确认: {desc}', plan_item_id=item.id)

                # 3. 等待用户确认 (2.4)
                confirmed = self._wait_for_confirmation(task_id, item.id)

                # 刷新 item 状态
                db.session.refresh(item)

                if not confirmed or item.status == 'skipped':
                    item.status = 'skipped'
                    item.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
                    self._log(task_id, 'info', 'user_action',
                              f'[{seq}] 用户跳过: {desc}', plan_item_id=item.id)
                    self._update_task_counts(task_id)
                    return

            # 4. 执行写操作（含 1 次自动重试）
            item.status = 'running'
            item.executed_at = datetime.now(timezone.utc)
            db.session.commit()

            start_ms = time.monotonic()
            try:
                result = self._call_api(item)
            except Exception as api_err:
                # 自动重试 1 次（ResourceInOperating 等暂态错误）
                if item.retry_count < 1:
                    item.retry_count += 1
                    db.session.commit()
                    self._log(task_id, 'warn', 'api_call',
                              f'[{seq}] API 失败，5s 后重试: {str(api_err)[:80]}',
                              plan_item_id=item.id)
                    time.sleep(5)
                    result = self._call_api(item)
                else:
                    raise
            duration = int((time.monotonic() - start_ms) * 1000)

            # 等待 CLB 实例完成操作（避免 ResourceInOperating）
            time.sleep(3)

            # 5. 保存结果
            item.status = 'success'
            item.response_data = result
            item.duration_ms = duration
            item.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            self._log(task_id, 'info', 'api_call',
                      f'[{seq}] ✓ 成功: {desc} ({duration}ms)',
                      plan_item_id=item.id,
                      detail=result)
            self._update_task_counts(task_id)

        except Exception as e:
            # 执行失败 (2.5)
            item.status = 'failed'
            item.error_message = str(e)
            item.retry_count += 1
            item.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            self._log(task_id, 'error', 'error',
                      f'[{seq}] ✗ 失败: {desc} — {str(e)}',
                      plan_item_id=item.id)
            self._update_task_counts(task_id)

            if fail_mode == 'pause':
                # 失败暂停模式 → 暂停任务
                task = db.session.get(MigrationTask, task_id)
                if task:
                    task.status = 'paused'
                    db.session.commit()
                self._log(task_id, 'info', 'system',
                          f'[{seq}] 失败暂停，等待用户操作（重试/跳过/终止）')
                self._wait_for_resume(task_id)
            # fail_mode == 'continue' → 记录后继续

    # ─── 2.4 确认等待机制 ────────────────────────────────────────

    def _wait_for_confirmation(self, task_id, item_id):
        """轮询等待用户确认（超时自动跳过）

        Returns:
            True = 用户确认, False = 跳过/超时
        """
        start = time.monotonic()
        while time.monotonic() - start < CONFIRM_TIMEOUT:
            time.sleep(CONFIRM_POLL_INTERVAL)

            # 刷新状态
            item = db.session.get(MigrationPlanItem, item_id)
            if item is None:
                return False

            db.session.refresh(item)

            if item.status == 'confirmed':
                return True
            elif item.status in ('skipped', 'cancelled'):
                return False
            elif item.status != 'waiting_confirm':
                # 状态被外部改变了
                return item.status == 'confirmed'

            # 检查任务是否被取消
            task = db.session.get(MigrationTask, task_id)
            if task and task.status == 'cancelled':
                return False

        # 超时 → 自动跳过
        item = db.session.get(MigrationPlanItem, item_id)
        if item and item.status == 'waiting_confirm':
            item.status = 'skipped'
            item.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            self._log(task_id, 'warn', 'system',
                      f'确认超时（{CONFIRM_TIMEOUT}s），自动跳过',
                      plan_item_id=item_id)
        return False

    # ─── 2.5 失败处理已在 _execute_single_item 中实现 ────────────

    # ─── 2.6 暂停/继续 ──────────────────────────────────────────

    def _wait_for_resume(self, task_id):
        """等待用户恢复或取消"""
        start = time.monotonic()
        while time.monotonic() - start < CONFIRM_TIMEOUT:
            time.sleep(CONFIRM_POLL_INTERVAL * 2)
            task = db.session.get(MigrationTask, task_id)
            if task is None:
                return
            db.session.refresh(task)
            if task.status in ('running', 'cancelled'):
                return

    # ─── 冲突检测 ────────────────────────────────────────────────

    def _detect_conflict(self, item):
        """写操作前冲突检测"""
        if item.operation_type not in ('create_listener',):
            return None

        params = item.request_params or {}
        protocol = params.get('Protocol', '')
        port = params.get('ListenerPort', 0)
        lb_id = item.target_instance_id

        if not lb_id or not protocol or not port:
            return None

        try:
            return self._writer.detect_conflict(lb_id, protocol, port)
        except Exception as e:
            logger.warning(f'冲突检测失败: {e}')
            return None

    # ─── API 调用 ────────────────────────────────────────────────

    def _call_api(self, item):
        """根据 operation_type 调用对应 API"""
        params = dict(item.request_params or {})  # 拷贝，避免修改原数据
        lb_id = item.target_instance_id

        if item.operation_type == 'create_listener':
            return self._writer.create_listener(lb_id, params)
        elif item.operation_type == 'create_rule':
            listener_id = params.pop('ListenerId', '')
            # 如果 ListenerId 为空，尝试从同一任务中前序 create_listener 的结果中获取
            if not listener_id:
                listener_id = self._resolve_listener_id(item)
            if not listener_id:
                raise ValueError(
                    f'缺少 ListenerId：请确保该监听器已创建成功。'
                    f'目标实例={lb_id}, 参数={params}')
            return self._writer.create_rule(lb_id, listener_id, params)
        else:
            raise ValueError(f'不支持的操作类型: {item.operation_type}')

    def _resolve_listener_id(self, rule_item):
        """从前序 create_listener 的执行结果中获取 ListenerId

        逻辑：找同任务中 target_instance_id 相同、operation_type=create_listener、
        status=success 的项，取其 response_data.listener_ids[0]。
        如果有多个监听器（不同端口），根据规则的端口/协议匹配。
        """
        params = rule_item.request_params or {}
        lb_id = rule_item.target_instance_id

        # 查找同任务中已成功的 create_listener 项
        prev_items = (db.session.query(MigrationPlanItem)
                      .filter_by(task_id=rule_item.task_id,
                                 target_instance_id=lb_id,
                                 operation_type='create_listener',
                                 status='success')
                      .order_by(MigrationPlanItem.seq_no.desc())
                      .all())

        for prev in prev_items:
            resp = prev.response_data or {}
            listener_ids = resp.get('listener_ids', [])
            if listener_ids:
                # 如果只有一个监听器或规则没指定端口，直接取第一个
                # 如果有多个，匹配协议（七层规则只属于 HTTP/HTTPS 监听器）
                prev_params = prev.request_params or {}
                prev_proto = prev_params.get('Protocol', '').upper()
                if prev_proto in ('HTTP', 'HTTPS'):
                    logger.info(f'自动关联 ListenerId: {listener_ids[0]} '
                                f'(来自 {prev.operation_desc})')
                    return listener_ids[0]

        # 最后手段：查询目标实例已有的 HTTP/HTTPS 监听器
        try:
            listeners = self._writer.describe_listeners(lb_id)
            for ls in listeners:
                if ls['Protocol'].upper() in ('HTTP', 'HTTPS'):
                    logger.info(f'从目标实例获取 ListenerId: {ls["ListenerId"]}')
                    return ls['ListenerId']
        except Exception as e:
            logger.warning(f'查询监听器失败: {e}')

        return ''

    # ─── 辅助方法 ────────────────────────────────────────────────

    def _update_task_counts(self, task_id):
        """更新任务统计"""
        task = db.session.get(MigrationTask, task_id)
        if not task:
            return

        items = db.session.query(MigrationPlanItem).filter_by(task_id=task_id).all()
        task.success_count = sum(1 for i in items if i.status == 'success')
        task.failed_count = sum(1 for i in items if i.status == 'failed')
        task.skipped_count = sum(1 for i in items if i.status == 'skipped')
        done = task.success_count + task.failed_count + task.skipped_count
        task.progress = round(done / max(task.total_items, 1) * 100, 2)
        db.session.commit()

    def _finalize_task(self, task_id):
        """执行完毕，更新任务最终状态"""
        task = db.session.get(MigrationTask, task_id)
        if not task:
            return

        self._update_task_counts(task_id)

        if task.failed_count > 0:
            task.status = 'completed'  # 有失败但执行完毕
        else:
            task.status = 'completed'
        task.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        self._log(task_id, 'info', 'system',
                  f'迁移完成: 成功 {task.success_count}, '
                  f'失败 {task.failed_count}, 跳过 {task.skipped_count}')

        # 自动生成迁移报告
        try:
            from app.services.migration.report_service import ReportService
            report = ReportService.create_from_task(task_id)
            self._log(task_id, 'info', 'system',
                      f'迁移报告已生成: id={report.id}')
        except Exception as e:
            logger.warning(f'自动生成报告失败(不影响迁移结果): {e}')

    def _log(self, task_id, level, log_type, message, plan_item_id=None, detail=None):
        """写入执行日志"""
        try:
            log_entry = ExecutionLog(
                task_id=task_id,
                plan_item_id=plan_item_id,
                log_level=level,
                log_type=log_type,
                message=message,
                detail=detail,
                logged_at=datetime.now(timezone.utc),
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.warning(f'写日志失败: {e}')
