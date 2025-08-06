"""pytest 配置文件."""

import os
import sys
from unittest.mock import MagicMock

# 添加项目路径到 sys.path
project_root = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.insert(0, project_root)

# Mock fastmcp.Context 以避免 MCP 初始化问题
sys.modules["fastmcp"] = MagicMock()
sys.modules["fastmcp.Context"] = MagicMock()

# Mock MCP server 相关模块
mock_mcp = MagicMock()
mock_mcp.tool = lambda: lambda func: func  # 返回原函数，不进行装饰
sys.modules["jenkins.server"] = MagicMock()
sys.modules["jenkins.server"].mcp = mock_mcp
