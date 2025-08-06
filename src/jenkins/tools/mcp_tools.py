"""Jenkins MCP tool interface."""

import logging
from typing import Any
from typing import List

from mcp.server.fastmcp import Context

from ..config import get_jenkins_servers
from ..server import mcp
from .client import JenkinsAPIClient
from .exceptions import JenkinsParameterError
from .scenarios import ScenarioManager
from .types import JobInfo
from .types import JobParameter
from .types import ParameterDict
from .types import ScenarioInfo
from .types import StopResult
from .types import TriggerResult

logger = logging.getLogger(__name__)


@mcp.tool()
def get_server_names() -> List[str]:
    """Get the list of all available Jenkins server names.

    Returns:
        List of server names
    """
    servers = get_jenkins_servers()
    return [server["name"] for server in servers]


@mcp.tool()
def get_scenario_list() -> List[ScenarioInfo]:
    """Get all available application scenarios - the preferred entry point for deployment tasks.

    Important: For any deployment-related task, this function should be called first instead of directly using search_jobs.
    This function returns a pre-configured scenario list, each containing the correct server and job path configuration.

    Returns:
        List of scenarios, each containing:
            - index: Scenario index (string)
            - name: Scenario name
            - description: Scenario description
            - server: Jenkins server name
            - job_path: Job path

    Workflow:
    1. Call this function to get the scenario list
    2. Let the user select a scenario
    3. Use search_jobs_by_scenario(scenario) to get the specific job
    4. Use trigger_build() to execute deployment
    """
    return ScenarioManager.get_scenario_list()


@mcp.tool()
def search_jobs_by_scenario(scenario: str) -> List[JobInfo]:
    """Get the specified Jenkins job directly by scenario.

    Args:
        scenario: Scenario name or index

    Returns:
        List of job info matching the scenario
    """
    return ScenarioManager.search_jobs_by_scenario(scenario)


@mcp.tool()
def search_jobs(server_name: str, keyword: str) -> List[JobInfo]:
    """Search Jenkins jobs on the specified server.

    Note: For deployment tasks, it is recommended to use get_scenario_list() and search_jobs_by_scenario().

    Args:
        server_name: Jenkins server name
        keyword: Search keyword

    Returns:
        List of matching jobs
    """
    client = JenkinsAPIClient(server_name)
    return client.search_jobs(keyword)


@mcp.tool()
def get_job_parameters(server_name: str, job_full_name: str) -> List[JobParameter]:
    """Get the parameter definitions of a Jenkins job.

    Args:
        server_name: Jenkins server name
        job_full_name: Full job name

    Returns:
        List of parameter definitions, including parameter name, type, default value, and options (if choice parameter)
    """
    client = JenkinsAPIClient(server_name)
    return client.get_job_parameters(job_full_name)


@mcp.tool()
def trigger_build(
    server_name: str, job_full_name: str, params: Any = None, ctx: Context = None
) -> TriggerResult:
    """Trigger Jenkins job build.

    Automatically determines parameter requirements and waits to obtain build_number.

    Args:
        server_name: Jenkins server name
        job_full_name: Full job name
        params: Optional parameter dict
        ctx: MCP context (for logging)

    Returns:
        Dict containing build_number or queue_id

    Raises:
        JenkinsParameterError: Missing required parameters
        JenkinsError: Trigger failed
    """
    client = JenkinsAPIClient(server_name)

    # Parameter type conversion
    build_params: ParameterDict = {}
    if params:
        if isinstance(params, dict):
            build_params = params
        else:
            # Try to convert other types
            try:
                build_params = dict(params)
            except (TypeError, ValueError):
                if ctx:
                    ctx.log(
                        "warning",
                        f"Invalid params type: {type(params)}, ignoring parameters",
                    )
                build_params = {}

    # Check required parameters
    job_params = client.get_job_parameters(job_full_name)
    if job_params:
        required_params = [p for p in job_params if p["default"] is None]
        missing_params = []

        for param in required_params:
            if not build_params or param["name"] not in build_params:
                missing_params.append(param)

        if missing_params:
            # Build detailed error message
            param_details = []
            for param in missing_params:
                detail = f"{param['name']} (type: {param['type']}, default: {param['default']}"
                if param.get("choices"):
                    detail += f", choices: {param['choices']}"
                detail += ")"
                param_details.append(detail)

            error_msg = f"This job requires required parameters, please provide them before execution. Missing parameters: {', '.join(param_details)}"
            raise JenkinsParameterError(error_msg, [p["name"] for p in missing_params])

    if ctx:
        ctx.log("info", f"Triggering build for {job_full_name} on {server_name}")
        if build_params:
            ctx.log("debug", f"Build parameters: {build_params}")

    return client.trigger_build(job_full_name, build_params)


@mcp.tool()
def get_build_status(server_name: str, job_full_name: str, build_number: int) -> dict:
    """Get the Jenkins build status for the specified build_number.

    Args:
        server_name: Jenkins server name
        job_full_name: Full job name
        build_number: Build number

    Returns:
        Build status info
    """
    client = JenkinsAPIClient(server_name)
    return client.get_build_status(job_full_name, build_number)


@mcp.tool()
def stop_build(
    server_name: str, job_full_name: str, build_number: int, ctx: Context = None
) -> StopResult:
    """Stop Jenkins build.

    Intelligently handles permission errors and will automatically check build status to confirm if it has already been terminated.

    Args:
        server_name: Jenkins server name
        job_full_name: Full job name
        build_number: Build number
        ctx: MCP context (for logging)

    Returns:
        Stop result
    """
    client = JenkinsAPIClient(server_name)

    if ctx:
        ctx.log(
            "info",
            f"Stopping build #{build_number} for {job_full_name} on {server_name}",
        )

    try:
        result = client.stop_build(job_full_name, build_number)

        if ctx:
            if result["status"] == "ALREADY_TERMINATED":
                ctx.log("info", "Build was already terminated")
            elif result["status"] == "STOP_REQUESTED":
                ctx.log("info", "Stop request sent successfully")
            elif result["status"] == "NOT_FOUND":
                ctx.log("warning", "Build not found")

        return result

    except Exception as e:
        if ctx:
            ctx.log("error", f"Failed to stop build: {e}")
        raise


@mcp.tool()
def get_build_log(server_name: str, job_full_name: str, build_number: int) -> str:
    """Get Jenkins build log.

    Args:
        server_name: Jenkins server name
        job_full_name: Full job name
        build_number: Build number

    Returns:
        Build log text
    """
    client = JenkinsAPIClient(server_name)
    return client.get_build_log(job_full_name, build_number)


@mcp.tool()
def validate_jenkins_config() -> dict:
    """Validate the integrity of Jenkins configuration.

    Returns:
        Validation result, including error list and status
    """
    errors = []

    # Validate server config
    try:
        servers = get_jenkins_servers()
        if not servers:
            errors.append("No Jenkins servers configured")
        else:
            for server in servers:
                required_fields = ["name", "uri", "user", "token"]
                for field in required_fields:
                    if field not in server or not server[field]:
                        errors.append(
                            f"Server '{server.get('name', 'unknown')}' missing field: {field}"
                        )
    except Exception as e:
        errors.append(f"Failed to load server configuration: {e}")

    # Validate scenario config
    scenario_errors = ScenarioManager.validate_scenario_config()
    errors.extend(scenario_errors)

    return {"valid": len(errors) == 0, "errors": errors, "error_count": len(errors)}


@mcp.tool()
def create_or_update_job_from_jenkinsfile(
    server_name: str,
    job_name: str,
    jenkinsfile_content: str,
    description: str = "",
    ctx: Context = None,
) -> dict:
    """Create or update a Jenkins job based on a Jenkinsfile.

    Args:
        server_name: Jenkins server name
        job_name: Name for the job (create if not exists, update if exists)
        jenkinsfile_content: Content of the Jenkinsfile (pipeline script)
        description: Optional job description
        ctx: MCP context (for logging)

    Returns:
        Dict containing job creation/update result with status and job_url

    Raises:
        JenkinsError: Job creation/update failed
    """
    client = JenkinsAPIClient(server_name)

    # Organize all jobs under MCPS/username directory
    # Get username from Jenkins server config, extract part before @ if it's an email
    server_config = client._server_config
    username = server_config.get("user", "unknown")
    if "@" in username:
        username = username.split("@")[0]

    final_folder_path = f"MCPS/{username}"
    job_full_name = f"{final_folder_path}/{job_name}"

    # Create job configuration XML for pipeline job
    job_config = f"""<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>{jenkinsfile_content}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>"""

    # Check if job already exists
    try:
        print(f"===job_full_name: {job_full_name}", flush=True)
        existing_job = client.get_job_info(job_full_name)
        print(f"=====existing_job: {existing_job}", flush=True)
        # Job exists, update it
        if ctx:
            ctx.log("info", f"Updating existing job '{job_name}' on {server_name}")
            ctx.log("debug", f"Target folder: {final_folder_path}")

        return client.update_job(job_name, job_config, final_folder_path)
    except Exception as e:
        # Job doesn't exist, create it
        print(e, flush=True)
        if ctx:
            ctx.log("info", f"Creating new job '{job_name}' on {server_name}")
            ctx.log("debug", f"Target folder: {final_folder_path}")

        return client.create_job(job_name, job_config, final_folder_path)
