"""Jenkins API client."""

import logging
import re
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests

from ..config import get_jenkins_servers
from .exceptions import JenkinsBuildNotFoundError
from .exceptions import JenkinsError
from .exceptions import JenkinsJobNotFoundError
from .exceptions import JenkinsPermissionError
from .exceptions import JenkinsServerNotFoundError
from .types import BuildInfo
from .types import JenkinsClient
from .types import JenkinsServerConfig
from .types import JobInfo
from .types import JobParameter
from .types import ParameterDict
from .types import QueueInfo
from .types import StopResult
from .types import TriggerResult

logger = logging.getLogger(__name__)


class JenkinsAPIClient:
    """Jenkins API client class."""

    def __init__(self, server_name: str, timeout: int = 30) -> None:
        """Initialize Jenkins API client.

        Args:
            server_name: Jenkins server name
            timeout: Request timeout (seconds)

        Raises:
            JenkinsServerNotFoundError: Server not found
        """
        self.server_name = server_name
        self.timeout = timeout
        self._server_config = self._get_server_config(server_name)
        self._client = JenkinsClient(self._server_config, timeout)

    @staticmethod
    def _get_server_config(server_name: str) -> JenkinsServerConfig:
        """Get server config.

        Args:
            server_name: Server name

        Returns:
            Server config dict

        Raises:
            JenkinsServerNotFoundError: Server not found
        """
        servers = get_jenkins_servers()
        for server in servers:
            if server["name"] == server_name:
                return server
        raise JenkinsServerNotFoundError(server_name)

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            **kwargs: Other request parameters

        Returns:
            HTTP response object

        Raises:
            JenkinsError: Request failed
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self._client.auth,
                params=params,
                timeout=self.timeout,
                **kwargs,
            )
            logger.debug(
                f"Jenkins API request: {method} {url} -> {response.status_code}"
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Jenkins API request failed: {e}")
            raise JenkinsError(f"Jenkins API request failed: {e}") from e

    def _build_job_url(self, job_full_name: str) -> str:
        """Build job URL.

        Args:
            job_full_name: Full job name

        Returns:
            Job URL
        """
        parts = job_full_name.split("/")
        job_path = "".join(f"/job/{part}" for part in parts)
        return f"{self._client.base_url}{job_path}"

    def get_job_info(self, job_full_name: str) -> JobInfo:
        """Get job info.

        Args:
            job_full_name: Full job name

        Returns:
            Job info

        Raises:
            JenkinsJobNotFoundError: Job not found
            JenkinsError: API request failed
        """
        job_url = self._build_job_url(job_full_name)
        api_url = f"{job_url}/api/json?tree=name,fullName,url,description,buildable,color,lastBuild[number,url]"

        response = self._make_request("GET", api_url)

        if response.status_code == 404:
            raise JenkinsJobNotFoundError(job_full_name, self.server_name)

        response.raise_for_status()
        data = response.json()

        # Get last build info
        last_build = data.get("lastBuild")
        last_build_number = None
        last_build_url = None

        if last_build:
            last_build_number = last_build.get("number")
            last_build_url = last_build.get("url")

        return {
            "name": data.get("name", ""),
            "fullName": data.get("fullName", job_full_name),
            "url": data.get("url", ""),
            "description": data.get("description"),
            "buildable": data.get("buildable", False),
            "color": data.get("color", "grey"),
            "is_parameterized": self._is_job_parameterized(job_full_name),
            "last_build_number": last_build_number,
            "last_build_url": last_build_url,
        }

    def _is_job_parameterized(self, job_full_name: str) -> bool:
        """Check if job is parameterized.

        Args:
            job_full_name: Full job name

        Returns:
            Whether parameterized
        """
        try:
            job_url = self._build_job_url(job_full_name)
            api_url = f"{job_url}/api/json?tree=property[parameterDefinitions[name]]"

            response = self._make_request("GET", api_url)
            response.raise_for_status()

            data = response.json()
            for prop in data.get("property", []):
                if "parameterDefinitions" in prop and prop["parameterDefinitions"]:
                    return True
            return False
        except Exception:
            logger.warning(f"Failed to check if job {job_full_name} is parameterized")
            return False

    def get_job_parameters(self, job_full_name: str) -> List[JobParameter]:
        """Get job parameter definitions.

        Args:
            job_full_name: Full job name

        Returns:
            List of parameter definitions

        Raises:
            JenkinsError: API request failed
        """
        job_url = self._build_job_url(job_full_name)
        api_url = (
            f"{job_url}/api/json?tree=actions[parameterDefinitions[name,type,"
            "defaultParameterValue[value],choices]],property[parameterDefinitions"
            "[name,type,defaultParameterValue[value],choices]]"
        )

        response = self._make_request("GET", api_url)
        response.raise_for_status()

        data = response.json()
        params = []

        def process_parameter(param_def: Dict[str, Any]) -> JobParameter:
            """Process parameter definition."""
            param_info: JobParameter = {
                "name": param_def.get("name", ""),
                "type": param_def.get("type", ""),
                "default": param_def.get("defaultParameterValue", {}).get("value"),
                "choices": None,
            }

            # If Choice Parameter, add choices list
            if (
                param_def.get("type") == "ChoiceParameterDefinition"
                and "choices" in param_def
            ):
                param_info["choices"] = param_def.get("choices", [])

            return param_info

        # Process property field
        for prop in data.get("property", []):
            if "parameterDefinitions" in prop:
                for param_def in prop["parameterDefinitions"]:
                    params.append(process_parameter(param_def))

        # Process actions field (compatibility)
        for action in data.get("actions", []):
            if "parameterDefinitions" in action:
                for param_def in action["parameterDefinitions"]:
                    params.append(process_parameter(param_def))

        return params

    def trigger_build(
        self, job_full_name: str, params: Optional[ParameterDict] = None
    ) -> TriggerResult:
        """Trigger build.

        Args:
            job_full_name: Full job name
            params: Build parameters

        Returns:
            Trigger result

        Raises:
            JenkinsError: Trigger failed
        """
        job_url = self._build_job_url(job_full_name)

        # Check job parameters
        job_params = self.get_job_parameters(job_full_name)

        if job_params:
            # Parameterized build
            build_url = f"{job_url}/buildWithParameters"
            build_params = params or {}
        else:
            # Non-parameterized build
            build_url = f"{job_url}/build"
            build_params = {}

        response = self._make_request("POST", build_url, params=build_params)
        response.raise_for_status()

        # Get queue location
        queue_location = response.headers.get("Location", "")
        queue_id = None

        if queue_location:
            match = re.search(r"/queue/item/(\d+)/", queue_location)
            if match:
                queue_id = int(match.group(1))

        # Wait for build to start
        return self._wait_for_build_start(queue_id, queue_location)

    def _wait_for_build_start(
        self, queue_id: Optional[int], queue_location: str
    ) -> TriggerResult:
        """Wait for build to start.

        Args:
            queue_id: Queue ID
            queue_location: Queue location URL

        Returns:
            Trigger result
        """
        max_attempts = 10

        for attempt in range(max_attempts):
            if queue_id:
                queue_info = self.get_queue_info(queue_id)
                if queue_info.get("build_number"):
                    return {
                        "status": "BUILD_STARTED",
                        "build_number": queue_info["build_number"],
                        "build_url": queue_info.get("build_url"),
                        "queue_id": queue_id,
                        "queue_url": queue_location,
                        "message": None,
                    }

            if attempt < max_attempts - 1:
                time.sleep(1)

        # Timeout, return queue info
        return {
            "status": "QUEUED",
            "build_number": None,
            "build_url": None,
            "queue_id": queue_id,
            "queue_url": queue_location,
            "message": "Build is queued but did not start within 10 seconds",
        }

    def get_queue_info(self, queue_id: int) -> QueueInfo:
        """Get queue info.

        Args:
            queue_id: Queue ID

        Returns:
            Queue info

        Raises:
            JenkinsError: API request failed
        """
        api_url = f"{self._client.base_url}/queue/item/{queue_id}/api/json"

        response = self._make_request("GET", api_url)

        if response.status_code == 404:
            return {
                "queue_id": queue_id,
                "blocked": False,
                "buildable": False,
                "stuck": False,
                "why": "Item not found",
                "build_number": None,
                "build_url": None,
                "status": "NOT_FOUND",
            }

        response.raise_for_status()
        data = response.json()

        result: QueueInfo = {
            "queue_id": queue_id,
            "blocked": data.get("blocked", False),
            "buildable": data.get("buildable", False),
            "stuck": data.get("stuck", False),
            "why": data.get("why"),
            "build_number": None,
            "build_url": None,
            "status": "QUEUED",
        }

        # Check if build has started
        executable = data.get("executable")
        if executable:
            result["build_number"] = executable.get("number")
            result["build_url"] = executable.get("url")
            result["status"] = "BUILD_STARTED"

        return result

    def get_build_status(self, job_full_name: str, build_number: int) -> BuildInfo:
        """Get build status.

        Args:
            job_full_name: Full job name
            build_number: Build number

        Returns:
            Build info

        Raises:
            JenkinsBuildNotFoundError: Build not found
            JenkinsError: API request failed
        """
        job_url = self._build_job_url(job_full_name)
        api_url = f"{job_url}/{build_number}/api/json"

        response = self._make_request("GET", api_url)

        if response.status_code == 404:
            raise JenkinsBuildNotFoundError(
                build_number, job_full_name, self.server_name
            )

        response.raise_for_status()
        data = response.json()

        return {
            "number": data.get("number", build_number),
            "result": data.get("result"),
            "building": data.get("building", False),
            "url": data.get("url", ""),
            "timestamp": data.get("timestamp", 0),
            "duration": data.get("duration", 0),
        }

    def stop_build(self, job_full_name: str, build_number: int) -> StopResult:
        """Stop build.

        Args:
            job_full_name: Full job name
            build_number: Build number

        Returns:
            Stop result

        Raises:
            JenkinsError: Stop failed
        """
        job_url = self._build_job_url(job_full_name)
        stop_url = f"{job_url}/{build_number}/stop"

        response = self._make_request("POST", stop_url)

        if response.status_code == 404:
            return {"status": "NOT_FOUND", "url": None}

        if response.status_code == 403:
            # Permission error, check build status
            return self._handle_stop_permission_error(job_full_name, build_number)

        response.raise_for_status()
        return {"status": "STOP_REQUESTED", "url": stop_url}

    def _handle_stop_permission_error(
        self, job_full_name: str, build_number: int
    ) -> StopResult:
        """Handle permission error when stopping build.

        Args:
            job_full_name: Full job name
            build_number: Build number

        Returns:
            Stop result
        """
        # Loop to check build status, confirm if already terminated
        for attempt in range(10):
            try:
                build_info = self.get_build_status(job_full_name, build_number)
                if not build_info.get("building", True):
                    return {"status": "ALREADY_TERMINATED", "url": None}
            except (JenkinsBuildNotFoundError, JenkinsError):
                # Build not found or query failed, consider as terminated
                return {"status": "ALREADY_TERMINATED", "url": None}

            if attempt < 9:
                time.sleep(1)

        # Still building after 10 checks, raise permission error
        raise JenkinsPermissionError("stop build", f"{job_full_name}#{build_number}")

    def get_build_log(self, job_full_name: str, build_number: int) -> str:
        """Get build log.

        Args:
            job_full_name: Full job name
            build_number: Build number

        Returns:
            Build log text

        Raises:
            JenkinsBuildNotFoundError: Build not found
            JenkinsError: API request failed
        """
        job_url = self._build_job_url(job_full_name)
        log_url = f"{job_url}/{build_number}/consoleText"

        response = self._make_request("GET", log_url)

        if response.status_code == 404:
            raise JenkinsBuildNotFoundError(
                build_number, job_full_name, self.server_name
            )

        response.raise_for_status()
        return response.text

    def search_jobs(self, keyword: str) -> List[JobInfo]:
        """Search jobs.

        Args:
            keyword: Search keyword

        Returns:
            List of matching jobs

        Raises:
            JenkinsError: API request failed
        """
        api_url = (
            f"{self._client.base_url}/api/json?tree=jobs[name,url,fullName,"
            "jobs[name,url,fullName,jobs[name,url,fullName,jobs[name,url,fullName]]]]"
        )

        response = self._make_request("GET", api_url)
        response.raise_for_status()

        data = response.json()
        all_jobs = self._collect_all_jobs(data.get("jobs", []))

        # Filter matching jobs
        matching_jobs = []
        for job in all_jobs:
            if (
                keyword.lower() in job["name"].lower()
                or keyword.lower() in job.get("fullName", "").lower()
            ):
                job_info = self.get_job_info(job["fullName"])
                matching_jobs.append(job_info)

        return matching_jobs

    def _collect_all_jobs(
        self, jobs: List[Dict[str, Any]], parent: str = ""
    ) -> List[Dict[str, Any]]:
        """Recursively collect all jobs.

        Args:
            jobs: List of jobs
            parent: Parent job path

        Returns:
            Flattened job list
        """
        result = []
        for job in jobs:
            name = job.get("fullName") or (
                f"{parent}/{job['name']}" if parent else job["name"]
            )
            result.append(
                {
                    "name": job["name"],
                    "fullName": name,
                    "url": job["url"],
                }
            )

            if "jobs" in job and job["jobs"]:
                result.extend(self._collect_all_jobs(job["jobs"], name))

        return result

    def create_job(self, job_name: str, job_config: str, folder_path: str = "") -> dict:
        """Create a new Jenkins job.

        Args:
            job_name: Name of the new job
            job_config: XML configuration for the job
            folder_path: Optional folder path (e.g., "test/folder1" for nested folders)

        Returns:
            Dict containing creation result with status and job_url

        Raises:
            JenkinsError: Job creation failed
        """
        # Create folders if they don't exist
        if folder_path:
            self._ensure_folders_exist(folder_path)
            folder_parts = folder_path.split("/")
            folder_url = "".join(f"/job/{part}" for part in folder_parts)
            create_url = f"{self._client.base_url}{folder_url}/createItem"
            job_url = f"{self._client.base_url}{folder_url}/job/{job_name}"
        else:
            create_url = f"{self._client.base_url}/createItem"
            job_url = f"{self._client.base_url}/job/{job_name}"

        # Create job
        headers = {"Content-Type": "application/xml"}
        params = {"name": job_name}

        response = self._make_request(
            "POST", create_url, params=params, data=job_config, headers=headers
        )

        if response.status_code == 400:
            raise JenkinsError(
                f"Job creation failed: Job '{job_name}' already exists or invalid configuration"
            )

        response.raise_for_status()

        return {
            "status": "CREATED",
            "job_name": job_name,
            "job_url": job_url,
            "folder_path": folder_path,
        }

    def _ensure_folders_exist(self, folder_path: str) -> None:
        """Ensure all folders in the path exist, create them if they don't.

        Args:
            folder_path: Folder path (e.g., "MCPS/username/subfolder")

        Raises:
            JenkinsError: Folder creation failed
        """
        folder_parts = folder_path.split("/")
        current_path = ""

        for folder in folder_parts:
            current_path = f"{current_path}/{folder}" if current_path else folder

            # Check if folder exists
            if not self._folder_exists(current_path):
                self._create_folder(current_path, folder)

    def _folder_exists(self, folder_path: str) -> bool:
        """Check if a folder exists.

        Args:
            folder_path: Folder path to check

        Returns:
            True if folder exists, False otherwise
        """
        try:
            folder_parts = folder_path.split("/")
            folder_url = "".join(f"/job/{part}" for part in folder_parts)
            api_url = f"{self._client.base_url}{folder_url}/api/json"

            response = self._make_request("GET", api_url)
            return response.status_code == 200
        except Exception:
            return False

    def _create_folder(self, folder_path: str, folder_name: str) -> None:
        """Create a folder.

        Args:
            folder_path: Full folder path
            folder_name: Name of the folder to create

        Raises:
            JenkinsError: Folder creation failed
        """
        # Determine parent path for folder creation
        folder_parts = folder_path.split("/")
        if len(folder_parts) > 1:
            parent_path = "/".join(folder_parts[:-1])
            parent_url = "".join(f"/job/{part}" for part in parent_path.split("/"))
            create_url = f"{self._client.base_url}{parent_url}/createItem"
        else:
            create_url = f"{self._client.base_url}/createItem"

        # Folder configuration XML
        folder_config = """<?xml version='1.1' encoding='UTF-8'?>
<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder">
  <actions/>
  <description></description>
  <properties/>
  <folderViews class="com.cloudbees.hudson.plugins.folder.views.DefaultFolderViewHolder">
    <views>
      <hudson.model.AllView>
        <owner class="com.cloudbees.hudson.plugins.folder.Folder" reference="../../../.."/>
        <name>all</name>
        <filterExecutors>false</filterExecutors>
        <filterQueue>false</filterQueue>
        <properties class="hudson.model.View$PropertyList"/>
      </hudson.model.AllView>
    </views>
    <tabBar class="hudson.views.DefaultViewsTabBar"/>
  </folderViews>
  <healthMetrics/>
  <icon class="com.cloudbees.hudson.plugins.folder.icons.StockFolderIcon"/>
</com.cloudbees.hudson.plugins.folder.Folder>"""

        headers = {"Content-Type": "application/xml"}
        params = {
            "name": folder_name,
            "mode": "com.cloudbees.hudson.plugins.folder.Folder",
        }

        response = self._make_request(
            "POST", create_url, params=params, data=folder_config, headers=headers
        )

        if response.status_code == 400:
            # Folder might already exist, check again
            if not self._folder_exists(folder_path):
                raise JenkinsError(f"Failed to create folder '{folder_name}'")
        else:
            response.raise_for_status()

    def update_job(self, job_name: str, job_config: str, folder_path: str = "") -> dict:
        """Update an existing Jenkins job.

        Args:
            job_name: Name of the job to update
            job_config: New XML configuration for the job
            folder_path: Folder path where the job is located

        Returns:
            Dict containing update result with status and job_url

        Raises:
            JenkinsError: Job update failed
        """
        # Build job URL based on folder path
        if folder_path:
            folder_parts = folder_path.split("/")
            folder_url = "".join(f"/job/{part}" for part in folder_parts)
            update_url = (
                f"{self._client.base_url}{folder_url}/job/{job_name}/config.xml"
            )
            job_url = f"{self._client.base_url}{folder_url}/job/{job_name}"
        else:
            update_url = f"{self._client.base_url}/job/{job_name}/config.xml"
            job_url = f"{self._client.base_url}/job/{job_name}"

        # Get CSRF token if needed
        headers = {"Content-Type": "application/xml"}

        try:
            crumb = self._get_crumb()
            if crumb:
                headers[crumb["crumbRequestField"]] = crumb["crumb"]
        except Exception:
            # If CSRF is disabled or we can't get crumb, continue without it
            pass

        # Try to update using POST to config.xml endpoint
        response = self._make_request(
            "POST", update_url, data=job_config, headers=headers
        )

        if response.status_code == 404:
            raise JenkinsError(f"Job update failed: Job '{job_name}' not found")
        else:
            response.raise_for_status()

        return {
            "status": "UPDATED",
            "job_name": job_name,
            "job_url": job_url,
            "folder_path": folder_path,
        }

    def _get_crumb(self) -> Optional[Dict[str, str]]:
        """Get CSRF crumb from Jenkins.

        Returns:
            Dict with crumb info or None if CSRF is disabled
        """
        try:
            crumb_url = f"{self._client.base_url}/crumbIssuer/api/json"
            response = self._make_request("GET", crumb_url)

            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
