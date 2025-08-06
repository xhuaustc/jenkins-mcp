"""Jenkins deployment scenario management."""

import logging
from typing import List

from ..config import get_scenario_mapping
from .client import JenkinsAPIClient
from .exceptions import JenkinsConfigurationError
from .exceptions import JenkinsError
from .types import JobInfo
from .types import ScenarioInfo

logger = logging.getLogger(__name__)


class ScenarioManager:
    """Jenkins deployment scenario manager."""

    @staticmethod
    def get_scenario_list() -> List[ScenarioInfo]:
        """Get all available application scenarios.

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

        Raises:
            JenkinsConfigurationError: Configuration error
        """
        try:
            scenario_mapping = get_scenario_mapping()
            scenarios = []

            for i, (name, config) in enumerate(scenario_mapping.items()):
                scenarios.append(
                    {
                        "index": str(i + 1),
                        "name": name,
                        "description": config["description"],
                        "server": config["server"],
                        "job_path": config["job_path"],
                    }
                )

            logger.info(f"Found {len(scenarios)} deployment scenarios")
            return scenarios

        except Exception as e:
            logger.error(f"Failed to get scenario list: {e}")
            raise JenkinsConfigurationError(f"Failed to get scenario list: {e}") from e

    @staticmethod
    def search_jobs_by_scenario(scenario: str) -> List[JobInfo]:
        """Get the specified Jenkins job directly by scenario.

        Args:
            scenario: Scenario name or index

        Returns:
            List of job info matching the scenario

        Raises:
            JenkinsConfigurationError: Scenario configuration error
            JenkinsError: API request failed
        """
        scenario_mapping = get_scenario_mapping()

        # Parse scenario name
        resolved_scenario = ScenarioManager._resolve_scenario_name(
            scenario, scenario_mapping
        )

        if resolved_scenario not in scenario_mapping:
            available_scenarios = ", ".join(scenario_mapping.keys())
            raise JenkinsConfigurationError(
                f"Unknown scenario '{scenario}'. Available scenarios: {available_scenarios}"
            )

        config = scenario_mapping[resolved_scenario]
        server_name = config["server"]
        job_path = config["job_path"].strip("/")

        logger.info(
            f"Searching jobs for scenario '{resolved_scenario}' on server '{server_name}'"
        )

        try:
            # Use Jenkins API client to get job info
            client = JenkinsAPIClient(server_name)
            job_info = client.get_job_info(job_path)

            # Add scenario-related info
            job_info["scenario"] = resolved_scenario
            job_info["scenario_match"] = True

            return [job_info]

        except Exception as e:
            logger.error(f"Failed to get job for scenario '{resolved_scenario}': {e}")
            if "404" in str(e) or "not found" in str(e).lower():
                raise JenkinsConfigurationError(
                    f"Job path '{job_path}' for scenario '{resolved_scenario}' not found on server '{server_name}'"
                ) from e
            else:
                raise JenkinsError(
                    f"Failed to get job for scenario '{resolved_scenario}': {e}"
                ) from e

    @staticmethod
    def _resolve_scenario_name(scenario: str, scenario_mapping: dict) -> str:
        """Parse scenario name (supports index).

        Args:
            scenario: Scenario name or index
            scenario_mapping: Scenario mapping config

        Returns:
            Parsed scenario name

        Raises:
            JenkinsConfigurationError: Invalid scenario
        """
        # If direct match, return
        if scenario in scenario_mapping:
            return scenario

        # Try to parse as index
        try:
            scenario_index = int(scenario) - 1
            scenario_names = list(scenario_mapping.keys())

            if 0 <= scenario_index < len(scenario_names):
                resolved_name = scenario_names[scenario_index]
                logger.debug(f"Resolved scenario #{scenario} to '{resolved_name}'")
                return resolved_name
            else:
                raise JenkinsConfigurationError(
                    f"Invalid scenario index: {scenario}. Valid range: 1-{len(scenario_names)}"
                )

        except ValueError:
            # Not a number, try fuzzy match
            for name in scenario_mapping.keys():
                if scenario.lower() in name.lower():
                    logger.debug(f"Fuzzy matched scenario '{scenario}' to '{name}'")
                    return name

            raise JenkinsConfigurationError(
                f"Unable to resolve scenario: {scenario}"
            ) from None

    @staticmethod
    def validate_scenario_config() -> List[str]:
        """Validate the integrity of scenario configuration.

        Returns:
            List of validation errors (empty list means no errors)
        """
        errors = []

        try:
            scenario_mapping = get_scenario_mapping()

            if not scenario_mapping:
                errors.append("No scenarios configured")
                return errors

            for scenario_name, config in scenario_mapping.items():
                # Check required fields
                required_fields = ["description", "server", "job_path"]
                for field in required_fields:
                    if field not in config:
                        errors.append(
                            f"Scenario '{scenario_name}' missing required field: {field}"
                        )

                # Check if server exists
                if "server" in config:
                    try:
                        JenkinsAPIClient._get_server_config(config["server"])
                    except Exception as e:
                        errors.append(
                            f"Scenario '{scenario_name}' references invalid server '{config['server']}': {e}"
                        )

        except Exception as e:
            errors.append(f"Failed to load scenario configuration: {e}")

        return errors
