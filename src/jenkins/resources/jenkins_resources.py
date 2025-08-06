"""Jenkins related resource management."""

from ..server import mcp


@mcp.resource()
def jenkins_connection_pool():
    """Jenkins connection pool resource (example, can be extended to actual pool implementation)."""
    # This is just an example, can be extended to a real connection pool or global session management
    return {"desc": "Jenkins connection pool/global session example resource"}
