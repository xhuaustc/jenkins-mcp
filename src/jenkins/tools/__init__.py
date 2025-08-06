"""Jenkins MCP 工具模块."""

# 导入所有 MCP 工具
from .mcp_tools import *  # noqa

# 导入核心组件供内部使用
from .client import JenkinsAPIClient
from .exceptions import (
    JenkinsError,
    JenkinsServerNotFoundError,
    JenkinsJobNotFoundError,
    JenkinsBuildNotFoundError,
    JenkinsPermissionError,
    JenkinsConfigurationError,
    JenkinsParameterError,
    JenkinsTimeoutError,
)
from .scenarios import ScenarioManager
from .types import (
    BuildStatus,
    JobColor,
    ParameterType,
    JenkinsServerConfig,
    JobInfo,
    JobParameter,
    BuildInfo,
    QueueInfo,
    TriggerResult,
    StopResult,
    ScenarioConfig,
    ScenarioInfo,
    JenkinsClient,
)

__all__ = [
    # MCP 工具函数（自动从 mcp_tools 导入）
    # 核心组件
    "JenkinsAPIClient",
    "ScenarioManager",
    # 异常类
    "JenkinsError",
    "JenkinsServerNotFoundError",
    "JenkinsJobNotFoundError",
    "JenkinsBuildNotFoundError",
    "JenkinsPermissionError",
    "JenkinsConfigurationError",
    "JenkinsParameterError",
    "JenkinsTimeoutError",
    # 类型定义
    "BuildStatus",
    "JobColor",
    "ParameterType",
    "JenkinsServerConfig",
    "JobInfo",
    "JobParameter",
    "BuildInfo",
    "QueueInfo",
    "TriggerResult",
    "StopResult",
    "ScenarioConfig",
    "ScenarioInfo",
    "JenkinsClient",
]
