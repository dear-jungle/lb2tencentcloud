"""迁移报告服务 — CRUD + 从执行结果自动生成"""
import logging
import json
from datetime import datetime, timezone

from app.extensions import db
from app.models.report import MigrationReport, ReportDetail
from app.models.migration_task import MigrationTask
from app.models.plan_item import MigrationPlanItem

logger = logging.getLogger(__name__)


class ReportService:
    """迁移报告管理服务"""

    # ─── 创建报告 ─────────────────────────────────

    @staticmethod
    def create_from_task(task_id):
        """从迁移任务执行结果创建报告

        Args:
            task_id: 迁移任务 ID

        Returns:
            MigrationReport 实例
        """
        with db.session.begin_nested():
            task = db.session.get(MigrationTask, task_id)
            if not task:
                raise ValueError(f'任务不存在: {task_id}')

            items = (db.session.query(MigrationPlanItem)
                     .filter_by(task_id=task_id)
                     .order_by(MigrationPlanItem.seq_no)
                     .all())

            success_count = sum(1 for i in items if i.status == 'success')
            failed_count = sum(1 for i in items if i.status == 'failed')
            skipped_count = sum(1 for i in items if i.status == 'skipped')
            total_items = len(items)

            now = datetime.now(timezone.utc)

            # 创建报告主记录
            report = MigrationReport(
                task_id=task_id,
                total_items=total_items,
                success_count=success_count,
                failed_count=failed_count,
                skipped_count=skipped_count,
                incompatible_count=sum(1 for i in items if i.error_message and 'incompatible' in str(i.operation_type).lower()),
                total_duration_ms=int((task.completed_at - task.started_at).total_seconds() * 1000) if task.completed_at and task.started_at else 0,
                generated_at=now,
                report_summary=_build_summary_text(success_count, failed_count, skipped_count),
                created_at=now,
            )
            db.session.add(report)
            db.session.flush()

            # 创建明细记录
            for item in items:
                category = _item_to_category(item.status)
                detail = ReportDetail(
                    report_id=report.id,
                    task_id=task_id,
                    plan_item_id=item.id,
                    category=category,
                    operation_type=item.operation_type or '',
                    operation_desc=item.operation_desc or '',
                    source_config=dict(item.request_params) if isinstance(item.request_params, dict) else item.request_params,
                    target_config=dict(item.response_data) if hasattr(item, 'response_data') and isinstance(item.response_data, dict) else None,
                    error_code='',
                    error_message=item.error_message or '',
                    incompatible_reason=item.error_message if category == 'incompatible' else '',
                    executed_at=item.completed_at,
                    duration_ms=item.duration_ms,
                    created_at=now,
                )
                db.session.add(detail)

            logger.info(f'报告已创建: id={report.id}, task_id={task_id}, '
                        f'总={total_items} 成功={success_count} 失败={failed_count}')
            return report

    # ─── 查询 ─────────────────────────────────────

    @staticmethod
    def list_reports(page=1, page_size=20):
        """分页查询报告列表"""
        query = db.session.query(MigrationReport).order_by(MigrationReport.created_at.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': [_report_to_dict(r) for r in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages,
        }

    @staticmethod
    def get_report(report_id):
        """获取单个报告（含明细）"""
        report = db.session.get(MigrationReport, report_id)
        if not report:
            return None

        details = (db.session.query(ReportDetail)
                  .filter_by(report_id=report_id)
                  .order_by(ReportDetail.created_at)
                  .all())

        return {
            **_report_to_dict(report),
            'details': [_detail_to_dict(d) for d in details],
        }

    # ─── 删除 ─────────────────────────────────────

    @staticmethod
    def delete_report(report_id):
        """删除报告及其级联明细"""
        report = db.session.get(MigrationReport, report_id)
        if not report:
            return False

        # 级联删除由数据库 CASCADE 处理
        db.session.delete(report)
        db.session.commit()
        logger.info(f'报告已删除: id={report_id}')
        return True


# ── 辅助函数 ────────────────────────────────────

def _build_summary_text(success, failed, skipped):
    total = success + failed + skipped
    rate = round(success / max(total, 1) * 100)
    if failed > 0:
        return f'存在 {failed} 个失败项，需人工处理'
    elif skipped > 0:
        return f'{skipped} 个项被跳过'
    else:
        return f'全部迁移成功 ({rate}%)'


def _item_to_category(status):
    mapping = {
        'success': 'success',
        'failed': 'failed',
        'skipped': 'skipped',
        'cancelled': 'skipped',
    }
    return mapping.get(status, 'incompatible')


def _report_to_dict(r):
    return {
        'id': r.id,
        'task_id': r.task_id,
        'total_items': r.total_items,
        'success_count': r.success_count,
        'failed_count': r.failed_count,
        'skipped_count': r.skipped_count,
        'incompatible_count': r.incompatible_count,
        'total_duration_ms': r.total_duration_ms,
        'generated_at': r.generated_at.isoformat() if r.generated_at else None,
        'report_summary': r.report_summary,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    }


def _detail_to_dict(d):
    return {
        'id': d.id,
        'category': d.category,
        'operation_type': d.operation_type,
        'operation_desc': d.operation_desc,
        'source_config': d.source_config,
        'target_config': d.target_config,
        'error_code': d.error_code,
        'error_message': d.error_message,
        'incompatible_reason': d.incompatible_reason,
        'duration_ms': d.duration_ms,
    }
