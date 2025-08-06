"""Custom exception classes for Jenkins MCP server."""

from typing import Optional


class JenkinsError(Exception):
    """Base exception for Jenkins operations."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        """Initialize Jenkins exception.

        Args:
            message: Error message
            status_code: HTTP status code (if applicable)
        """
        super().__init__(message)
        self.status_code = status_code


class JenkinsServerNotFoundError(JenkinsError):
    """Exception for Jenkins server not found."""

    def __init__(self, server_name: str) -> None:
        """Initialize server not found exception.

        Args:
            server_name: Server name
        """
        super().__init__(f"Jenkins server '{server_name}' not found")
        self.server_name = server_name


class JenkinsJobNotFoundError(JenkinsError):
    """Exception for Jenkins job not found."""

    def __init__(self, job_name: str, server_name: str) -> None:
        """Initialize job not found exception.

        Args:
            job_name: Job name
            server_name: Server name
        """
        super().__init__(
            f"Jenkins job '{job_name}' not found on server '{server_name}'"
        )
        self.job_name = job_name
        self.server_name = server_name


class JenkinsBuildNotFoundError(JenkinsError):
    """Exception for Jenkins build not found."""

    def __init__(self, build_number: int, job_name: str, server_name: str) -> None:
        """Initialize build not found exception.

        Args:
            build_number: Build number
            job_name: Job name
            server_name: Server name
        """
        super().__init__(
            f"Jenkins build #{build_number} for job '{job_name}' "
            f"not found on server '{server_name}'"
        )
        self.build_number = build_number
        self.job_name = job_name
        self.server_name = server_name


class JenkinsPermissionError(JenkinsError):
    """Exception for Jenkins permission error."""

    def __init__(self, operation: str, resource: str) -> None:
        """Initialize permission error exception.

        Args:
            operation: Operation type
            resource: Resource name
        """
        super().__init__(f"Permission denied for {operation} on {resource}")
        self.operation = operation
        self.resource = resource


class JenkinsConfigurationError(JenkinsError):
    """Exception for Jenkins configuration error."""

    def __init__(self, message: str) -> None:
        """Initialize configuration error exception.

        Args:
            message: Error message
        """
        super().__init__(f"Jenkins configuration error: {message}")


class JenkinsParameterError(JenkinsError):
    """Exception for Jenkins parameter error."""

    def __init__(self, message: str, missing_params: Optional[list] = None) -> None:
        """Initialize parameter error exception.

        Args:
            message: Error message
            missing_params: List of missing parameters
        """
        super().__init__(message)
        self.missing_params = missing_params or []


class JenkinsTimeoutError(JenkinsError):
    """Exception for Jenkins operation timeout."""

    def __init__(self, operation: str, timeout_seconds: int) -> None:
        """Initialize timeout exception.

        Args:
            operation: Operation type
            timeout_seconds: Timeout in seconds
        """
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds
