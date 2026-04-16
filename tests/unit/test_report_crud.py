"""迁移报告 CRUD 接口测试"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestReportList:
    """GET /api/reports"""

    def test_empty_list(self, client):
        """无报告时返回空列表"""
        with patch('app.services.migration.report_service.ReportService.list_reports') as mock:
            mock.return_value = {'items': [], 'total': 0, 'page': 1, 'pages': 0}
            resp = client.get('/api/reports?page=1&page_size=20')
            data = resp.get_json()
            assert data['success'] is True
            assert data['data']['total'] == 0

    def test_pagination_params(self, client):
        """分页参数正确传递"""
        with patch('app.services.migration.report_service.ReportService.list_reports') as mock:
            mock.return_value = {'items': [], 'total': 5, 'page': 2, 'pages': 1}
            resp = client.get('/api/reports?page=2&page_size=10')
            mock.assert_called_once_with(page=2, page_size=10)


class TestReportDetail:
    """GET /api/reports/<id>"""

    def test_get_existing_report(self, client):
        """获取存在的报告详情"""
        report_data = {
            'id': 1, 'task_id': 10, 'total_items': 5, 'success_count': 4,
            'failed_count': 1, 'skipped_count': 0, 'incompatible_count': 0,
            'total_duration_ms': 30000, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'report_summary': '部分成功', 'created_at': datetime.now(timezone.utc).isoformat(),
            'details': [
                {'id': 100, 'category': 'success', 'operation_type': 'create_listener',
                 'operation_desc': 'TCP:80', 'error_message': '', 'duration_ms': 1500},
                {'id': 101, 'category': 'failed', 'operation_type': 'create_rule',
                 'operation_desc': 'HTTP /api', 'error_message': '端口冲突', 'duration_ms': 800},
            ],
        }
        with patch('app.services.migration.report_service.ReportService.get_report') as mock:
            mock.return_value = report_data
            resp = client.get('/api/reports/1')
            data = resp.get_json()
            assert data['success'] is True
            assert data['data']['id'] == 1
            assert len(data['data']['details']) == 2

    def test_get_nonexistent_report(self, client):
        """获取不存在的报告返回 404"""
        with patch('app.services.migration.report_service.ReportService.get_report') as mock:
            mock.return_value = None
            resp = client.get('/api/reports/99999')
            assert resp.status_code == 404


class TestReportDelete:
    """DELETE /api/reports/<id>"""

    def test_delete_existing(self, client):
        """删除存在的报告"""
        with patch('app.services.migration.report_service.ReportService.delete_report') as mock:
            mock.return_value = True
            resp = client.delete('/api/reports/1')
            data = resp.get_json()
            assert data['success'] is True

    def test_delete_nonexistent(self, client):
        """删除不存在的报告返回 404"""
        with patch('app.services.migration.report_service.ReportService.delete_report') as mock:
            mock.return_value = False
            resp = client.delete('/api/reports/99999')
            assert resp.status_code == 404


class TestBatchDownload:
    """POST /api/report/batch-download"""

    def test_batch_download_with_ids(self, client):
        """提供 ID 列表触发批量下载"""
        with patch('app.services.migration.report_service.ReportService.get_report') as mock_get:
            mock_get.return_value = {
                'id': 1, 'task_id': 10, 'total_items': 3, 'success_count': 3,
                'failed_count': 0, 'skipped_count': 0, 'incompatible_count': 0,
                'report_summary': '全部成功', 'details': [],
            }
            resp = client.post('/api/report/batch-download',
                               json={'ids': [1]},
                               content_type='application/json')
            # 应该返回 ZIP 文件或成功响应
            assert resp.status_code == 200

    def test_batch_download_no_ids(self, client):
        """不提供 ID 返回 400"""
        resp = client.post('/api/report/batch-download',
                           json={},
                           content_type='application/json')
        assert resp.status_code == 400


class TestReportDownload:
    """GET /api/reports/<id>/download"""

    def test_excel_download_format(self, client):
        """Excel 格式下载请求"""
        with patch('app.services.migration.report_service.ReportService.get_report') as mock:
            mock.return_value = {
                'id': 1, 'total_items': 2, 'success_count': 2, 'failed_count': 0,
                'skipped_count': 0, 'report_summary': '', 'details': [],
            }
            resp = client.get('/api/reports/1/download?format=excel')
            assert resp.status_code == 200
            assert 'xlsx' in resp.content_type or 'octet-stream' in resp.content_type

    def test_json_download_format(self, client):
        """JSON 格式下载请求"""
        with patch('app.services.migration.report_service.ReportService.get_report') as mock:
            mock.return_value = {
                'id': 1, 'total_items': 1, 'success_count': 1,
                'failed_count': 0, 'skipped_count': 0, 'report_summary': '', 'details': [],
            }
            resp = client.get('/api/reports/1/download?format=json')
            assert resp.status_code == 200
            assert 'json' in resp.content_type
