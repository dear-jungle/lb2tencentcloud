"""目标端冲突检测 API 测试"""
import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestDetectTargetConflicts:
    """POST /api/mapping/detect-target-conflicts"""

    ENDPOINT = '/api/mapping/detect-target-conflicts'

    def test_missing_target_id(self, client):
        """缺少 targetInstanceId 返回 400"""
        resp = client.post(self.ENDPOINT,
                            json={'listeners': [{'listener_protocol': 'TCP', 'listener_port': 80}]},
                            content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_empty_listeners_no_conflict(self, client):
        """空 listeners 列表返回无冲突"""
        with patch('app.routes.mapping_routes._get_tencent_writer') as mock_writer:
            mock_writer.return_value = MagicMock()
            mock_writer.return_value.describe_listeners.return_value = []

            resp = client.post(self.ENDPOINT,
                                json={'targetInstanceId': 'lb-xxx', 'listeners': []},
                                content_type='application/json')
            data = resp.get_json()
            assert data['success'] is True
            assert data['data']['has_conflict'] is False
            assert len(data['data']['conflicts']) == 0

    def test_has_conflict(self, client):
        """目标实例已有相同协议:端口监听器时返回冲突"""
        with patch('app.routes.mapping_routes._get_tencent_writer') as mock_writer:
            writer_mock = MagicMock()
            writer_mock.describe_listeners.return_value = [
                {'ListenerId': 'lst-abc123', 'Protocol': 'TCP', 'Port': 80, 'ListenerName': 'test-listener'},
                {'ListenerId': 'lst-def456', 'Protocol': 'HTTP', 'Port': 443, 'ListenerName': 'https-listener'},
            ]
            mock_writer.return_value = writer_mock

            resp = client.post(self.ENDPOINT,
                                json={
                                    'targetInstanceId': 'lb-xxx',
                                    'listeners': [
                                        {'listener_protocol': 'tcp', 'listener_port': 80},
                                    ],
                                },
                                content_type='application/json')
            data = resp.get_json()
            assert data['success'] is True
            assert data['data']['has_conflict'] is True
            assert len(data['data']['conflicts']) == 1
            conflict = data['data']['conflicts'][0]
            assert conflict['port'] == 80
            assert conflict['existing_listener_id'] == 'lst-abc123'

    def test_no_conflict_different_port(self, client):
        """不同端口无冲突"""
        with patch('app.routes.mapping_routes._get_tencent_writer') as mock_writer:
            writer_mock = MagicMock()
            writer_mock.describe_listeners.return_value = [
                {'ListenerId': 'lst-abc', 'Protocol': 'TCP', 'Port': 443, 'ListenerName': 'ssl'},
            ]
            mock_writer.return_value = writer_mock

            resp = client.post(self.ENDPOINT,
                                json={
                                    'targetInstanceId': 'lb-xxx',
                                    'listeners': [
                                        {'listener_protocol': 'TCP', 'listener_port': 80},
                                    ],
                                },
                                content_type='application/json')
            data = resp.get_json()
            assert data['data']['has_conflict'] is False

    def test_no_creds_401(self, client):
        """未设置腾讯云凭证返回 401"""
        with patch('app.routes.mapping_routes._get_tencent_writer') as mock_writer:
            mock_writer.return_value = None

            resp = client.post(self.ENDPOINT,
                                json={'targetInstanceId': 'lb-xxx', 'listeners': [{'listener_protocol': 'TCP', 'listener_port': 80}]},
                                content_type='application/json')
            assert resp.status_code == 401

    @patch('app.routes.mapping_routes._get_tencent_writer')
    def test_api_exception_handled(self, mock_writer, client):
        """API 调用异常返回 500"""
        mock_writer.return_value = MagicMock()
        mock_writer.return_value.describe_listeners.side_effect = Exception("网络错误")

        resp = client.post(self.ENDPOINT,
                            json={'targetInstanceId': 'lb-xxx', 'listeners': [{'listener_protocol': 'TCP', 'listener_port': 80}]},
                            content_type='application/json')
        assert resp.status_code == 500
