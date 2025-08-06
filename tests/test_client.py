"""Jenkins API 客户端测试."""

from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests
from jenkins.tools.client import JenkinsAPIClient
from jenkins.tools.exceptions import JenkinsBuildNotFoundError
from jenkins.tools.exceptions import JenkinsError
from jenkins.tools.exceptions import JenkinsJobNotFoundError
from jenkins.tools.exceptions import JenkinsServerNotFoundError


class TestJenkinsAPIClient:
    """Jenkins API 客户端测试类."""

    def test_init_with_valid_server(self):
        """测试使用有效服务器初始化客户端."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            client = JenkinsAPIClient("test-server")
            assert client.server_name == "test-server"
            assert client.timeout == 30

    def test_init_with_invalid_server(self):
        """测试使用无效服务器初始化客户端."""
        with patch("jenkins.tools.client.get_jenkins_servers", return_value=[]):
            with pytest.raises(JenkinsServerNotFoundError):
                JenkinsAPIClient("nonexistent-server")

    def test_build_job_url(self):
        """测试构建任务 URL."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            client = JenkinsAPIClient("test-server")

            # 测试简单任务名
            url = client._build_job_url("my-job")
            assert url == "http://test.jenkins.com/job/my-job"

            # 测试嵌套任务名
            url = client._build_job_url("folder/sub-folder/my-job")
            assert url == "http://test.jenkins.com/job/folder/job/sub-folder/job/my-job"

    @patch("requests.request")
    def test_get_job_info_success(self, mock_request):
        """测试成功获取任务信息."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        # 模拟 API 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test-job",
            "fullName": "test-job",
            "url": "http://test.jenkins.com/job/test-job/",
            "description": "Test job",
            "buildable": True,
            "color": "blue",
        }
        mock_request.return_value = mock_response

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            with patch.object(
                JenkinsAPIClient, "_is_job_parameterized", return_value=False
            ):
                client = JenkinsAPIClient("test-server")
                job_info = client.get_job_info("test-job")

                assert job_info["name"] == "test-job"
                assert job_info["fullName"] == "test-job"
                assert job_info["buildable"] is True
                assert job_info["is_parameterized"] is False

    @patch("requests.request")
    def test_get_job_info_not_found(self, mock_request):
        """测试获取不存在的任务信息."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        # 模拟 404 响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            client = JenkinsAPIClient("test-server")

            with pytest.raises(JenkinsJobNotFoundError):
                client.get_job_info("nonexistent-job")

    @patch("requests.request")
    def test_get_build_status_success(self, mock_request):
        """测试成功获取构建状态."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        # 模拟 API 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 123,
            "result": "SUCCESS",
            "building": False,
            "url": "http://test.jenkins.com/job/test-job/123/",
            "timestamp": 1234567890,
            "duration": 60000,
        }
        mock_request.return_value = mock_response

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            client = JenkinsAPIClient("test-server")
            build_info = client.get_build_status("test-job", 123)

            assert build_info["number"] == 123
            assert build_info["result"] == "SUCCESS"
            assert build_info["building"] is False

    @patch("requests.request")
    def test_get_build_status_not_found(self, mock_request):
        """测试获取不存在的构建状态."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        # 模拟 404 响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            client = JenkinsAPIClient("test-server")

            with pytest.raises(JenkinsBuildNotFoundError):
                client.get_build_status("test-job", 999)

    @patch("requests.request")
    def test_make_request_network_error(self, mock_request):
        """测试网络错误处理."""
        mock_config = {
            "name": "test-server",
            "uri": "http://test.jenkins.com",
            "user": "test-user",
            "token": "test-token",
        }

        # 模拟网络错误
        mock_request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        with patch(
            "jenkins.tools.client.get_jenkins_servers", return_value=[mock_config]
        ):
            client = JenkinsAPIClient("test-server")

            # 临时禁用错误日志以避免在测试中显示预期的错误
            with patch("jenkins.tools.client.logger") as mock_logger:
                with pytest.raises(JenkinsError):
                    client.get_job_info("test-job")

                # 验证错误确实被记录了（但不会打印到控制台）
                mock_logger.error.assert_called_once()
