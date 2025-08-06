"""Main entry point for the jenkins MCP server.

This module allows the package to be run as a module:
python -m jenkins
"""

import argparse
import sys


def main():
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Jenkins MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="MCP transport type (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP/SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--scenarios",
        "-s",
        help="Path to scenarios YAML file (will be merged with default scenarios)",
    )

    args = parser.parse_args()

    try:
        # Set configuration arguments before importing server
        from jenkins.server import set_config_args

        set_config_args(config_path=args.config, scenarios_path=args.scenarios)

        # Import server module and create MCP instance with proper config
        if args.transport == "stdio":
            from jenkins.server import mcp

            return mcp.run()
        else:
            # Create MCP server with custom host/port for HTTP/SSE modes
            from jenkins.server import create_mcp_server

            mcp = create_mcp_server(host=args.host, port=args.port)
            return mcp.run(transport=args.transport)
    except Exception as e:
        print(f"Error running MCP server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
