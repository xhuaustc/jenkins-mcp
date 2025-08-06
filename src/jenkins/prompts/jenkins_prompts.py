"""Jenkins related prompts."""

from ..config import get_scenario_mapping
from ..server import mcp


@mcp.prompt()
def scenario_selection_prompt() -> str:
    """Generate a prompt for scenario selection to help the user choose the appropriate application scenario."""
    scenario_mapping = get_scenario_mapping()
    scenarios = list(scenario_mapping.keys())
    scenario_list = "\n".join(
        [
            f"- {i + 1}. {scenario}: {scenario_mapping[scenario]['description']}"
            for i, scenario in enumerate(scenarios)
        ]
    )

    return (
        f"Please select your application scenario:\n{scenario_list}\n\n"
        "Please reply with the scenario name or number, and I will provide you with the corresponding Jenkins configuration and operation guidance."
    )


@mcp.prompt()
def scenario_guidance_prompt(scenario: str) -> str:
    """Generate a guidance prompt based on the user's selected scenario."""
    scenario_mapping = get_scenario_mapping()
    if scenario not in scenario_mapping:
        # Try to parse as index
        try:
            scenario_index = int(scenario) - 1
            scenario_names = list(scenario_mapping.keys())
            if 0 <= scenario_index < len(scenario_names):
                scenario = scenario_names[scenario_index]
            else:
                return f"Invalid scenario selection: {scenario}. Please use the scenario name or a valid number."
        except ValueError:
            return f"Unrecognized scenario: {scenario}. Please use the scenario name or number."

    config = scenario_mapping[scenario]
    return config["prompt_template"].format(
        job_path=config["job_path"], server=config["server"]
    )


@mcp.prompt()
def get_scenario_config(scenario: str) -> dict:
    """Get the complete configuration information for the specified scenario."""
    scenario_mapping = get_scenario_mapping()
    if scenario not in scenario_mapping:
        # Try to parse as index
        try:
            scenario_index = int(scenario) - 1
            scenario_names = list(scenario_mapping.keys())
            if 0 <= scenario_index < len(scenario_names):
                scenario = scenario_names[scenario_index]
            else:
                return {"error": f"Invalid scenario selection: {scenario}"}
        except ValueError:
            return {"error": f"Unrecognized scenario: {scenario}"}

    return scenario_mapping[scenario]


@mcp.prompt()
def job_description_prompt(server_name: str, job_name: str) -> str:
    """Generate a brief description prompt for a Jenkins job."""
    return f"Please briefly introduce the purpose, main process, and trigger method of job `{job_name}` on Jenkins server `{server_name}`."


@mcp.prompt()
def build_result_summary_prompt(
    server_name: str, job_name: str, build_number: int, result: str
) -> str:
    """Generate a Jenkins build result interpretation prompt."""
    print("--------------------------------")
    print(f"server_name: {server_name}")
    print(f"job_name: {job_name}")
    print(f"build_number: {build_number}")
    print(f"result: {result}")
    print("--------------------------------")
    return (
        f"Please interpret the result of build #{build_number} for job `{job_name}` on Jenkins server `{server_name}` in plain language: {result}."
        "If failed, please analyze possible reasons; if successful, briefly describe the key steps."
    )


@mcp.prompt()
def build_log_analysis_prompt(
    server_name: str, job_name: str, build_number: int, log_excerpt: str
) -> str:
    """Generate a Jenkins build log analysis prompt."""
    return (
        f"Please analyze the following log excerpt from build #{build_number} for job `{job_name}` on Jenkins server `{server_name}` and identify any errors or exceptions:\n"
        f"Log excerpt:\n{log_excerpt}"
    )


@mcp.prompt()
def trigger_job_prompt(
    server_name: str, job_name: str, is_parameterized: bool, parameters: list = None
) -> str:
    """Generate a prompt for triggering a job."""
    if is_parameterized:
        param_list = "\n".join(
            [
                f"- {p['name']} (type: {p['type']}, default: {p['default']})"
                for p in (parameters or [])
            ]
        )
        return (
            f"You are trying to trigger a parameterized job `{job_name}` on Jenkins server `{server_name}`.\n"
            f"This job requires the following parameters, please provide them before execution:\n{param_list}"
        )
    else:
        return f"You are trying to trigger job `{job_name}` on Jenkins server `{server_name}`. This job does not require parameters and can be executed directly."
