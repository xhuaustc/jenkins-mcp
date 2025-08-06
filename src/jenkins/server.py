"""jenkins MCP server.

Model Context Protocol server that initializes tools, resources, and prompts.
Includes lifecycle management and configuration handling.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

# Import config management
from .config import load_config

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Type-safe application context container.

    Store any application-wide state or connections here.
    """

    config: dict


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Application lifecycle manager.

    Handles startup and shutdown operations with proper resource management.

    Args:
        server: The FastMCP server instance

    Yields:
        The application context with initialized resources
    """
    # Load configuration with global args
    config = load_config(
        config_path=_config_args.get("config_path"),
        scenarios_path=_config_args.get("scenarios_path"),
    )
    logger.info("Server starting up...")
    try:
        context = AppContext(config=config)
        yield context
    finally:
        logging.info("Server shutting down...")


# Global configuration storage
_config_args = {}

# Global MCP server instance
mcp = None


def set_config_args(config_path: str = None, scenarios_path: str = None):
    """设置全局配置参数."""
    global _config_args
    _config_args = {
        "config_path": config_path,
        "scenarios_path": scenarios_path,
    }


def create_mcp_server(host: str = "0.0.0.0", port: int = 8000) -> FastMCP:
    """Create a FastMCP server instance with the specified host and port."""
    global mcp
    mcp = FastMCP(
        "jenkins",  # Server name
        lifespan=app_lifespan,  # Lifecycle manager
        dependencies=["mcp>=1.0"],  # Required dependencies
        host=host,  # Bind host
        port=port,  # Bind port
        # TODO: add more settings for FastMCP
    )

    # Import tools, resources, and prompts after setting the global mcp
    _import_modules()

    return mcp


def _import_modules():
    """Import all tools, resources, and prompts modules."""
    # These imports register wit    h the global mcp instance

    import jenkins.tools  # noqa
    import jenkins.resources  # noqa
    import jenkins.prompts  # noqa


# Create the default MCP server with default settings
mcp = create_mcp_server()

# Make the server instance accessible to other modules
server = mcp
