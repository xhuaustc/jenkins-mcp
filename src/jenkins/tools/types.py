"""Jenkins MCP server type definitions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from typing_extensions import TypedDict


class BuildStatus(str, Enum):
    """Build status enum."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNSTABLE = "UNSTABLE"
    ABORTED = "ABORTED"
    NOT_BUILT = "NOT_BUILT"
    UNKNOWN = "UNKNOWN"


class JobColor(str, Enum):
    """Job color status enum."""

    BLUE = "blue"
    BLUE_ANIME = "blue_anime"
    RED = "red"
    RED_ANIME = "red_anime"
    YELLOW = "yellow"
    YELLOW_ANIME = "yellow_anime"
    GREY = "grey"
    GREY_ANIME = "grey_anime"
    DISABLED = "disabled"
    ABORTED = "aborted"
    ABORTED_ANIME = "aborted_anime"
    NOTBUILT = "notbuilt"
    NOTBUILT_ANIME = "notbuilt_anime"


class ParameterType(str, Enum):
    """Parameter type enum."""

    STRING = "StringParameterDefinition"
    BOOLEAN = "BooleanParameterDefinition"
    CHOICE = "ChoiceParameterDefinition"
    PASSWORD = "PasswordParameterDefinition"
    TEXT = "TextParameterDefinition"
    FILE = "FileParameterDefinition"


# TypedDict definitions
class JenkinsServerConfig(TypedDict):
    """Jenkins server config."""

    name: str
    uri: str
    user: str
    token: str


class JobInfo(TypedDict):
    """Job info."""

    name: str
    fullName: str
    url: str
    description: Optional[str]
    buildable: bool
    color: str
    is_parameterized: bool
    last_build_number: Optional[int]
    last_build_url: Optional[str]


class JobParameter(TypedDict):
    """Job parameter definition."""

    name: str
    type: str
    default: Optional[Any]
    choices: Optional[List[str]]


class BuildInfo(TypedDict):
    """Build info."""

    number: int
    result: Optional[str]
    building: bool
    url: str
    timestamp: int
    duration: int


class QueueInfo(TypedDict):
    """Queue info."""

    queue_id: int
    blocked: bool
    buildable: bool
    stuck: bool
    why: Optional[str]
    build_number: Optional[int]
    build_url: Optional[str]
    status: str


class TriggerResult(TypedDict):
    """Trigger build result."""

    status: Literal["BUILD_STARTED", "QUEUED"]
    build_number: Optional[int]
    build_url: Optional[str]
    queue_id: Optional[int]
    queue_url: Optional[str]
    message: Optional[str]


class StopResult(TypedDict):
    """Stop build result."""

    status: Literal["STOP_REQUESTED", "ALREADY_TERMINATED", "NOT_FOUND"]
    url: Optional[str]


class ScenarioConfig(TypedDict):
    """Scenario config."""

    description: str
    server: str
    job_path: str
    prompt_template: str


class ScenarioInfo(TypedDict):
    """Scenario info."""

    index: str
    name: str
    description: str
    server: str
    job_path: str


@dataclass
class JenkinsClient:
    """Jenkins client config."""

    server_config: JenkinsServerConfig
    timeout: int = 30

    @property
    def base_url(self) -> str:
        """Get base URL."""
        return self.server_config["uri"].rstrip("/")

    @property
    def auth(self) -> tuple[str, str]:
        """Get authentication info."""
        return (self.server_config["user"], self.server_config["token"])


# Union types
JobResult = Union[JobInfo, List[JobInfo]]
BuildResult = Union[BuildInfo, TriggerResult, StopResult]
ParameterValue = Union[str, int, bool, None]
ParameterDict = Dict[str, ParameterValue]

# Response types
JenkinsAPIResponse = Dict[str, Any]
HttpStatusCode = int
