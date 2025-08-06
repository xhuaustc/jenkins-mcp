"""Configuration management for the MCP server.

Handles loading configuration from environment variables and/or config files.
"""

import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Optional

import yaml


def load_default_scenarios() -> Dict[str, Any]:
    """Load default scenario configuration."""
    default_scenarios_file = (
        Path(__file__).parent.parent.parent / "scenarios.default.yaml"
    )

    if default_scenarios_file.exists():
        try:
            with open(default_scenarios_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("scenarios", {})
        except Exception as e:
            print(f"Warning: Failed to load default scenarios: {e}")


def load_user_scenarios(scenarios_path: Optional[str] = None) -> Dict[str, Any]:
    """Load user-defined scenario configuration."""
    scenarios = {}

    # Check for scenario file specified by environment variable
    env_scenarios_file = os.getenv("JENKINS_MCP_SCENARIOS_FILE")
    if env_scenarios_file and Path(env_scenarios_file).exists():
        scenarios_path = env_scenarios_file

    # If no path specified, try default locations
    if not scenarios_path:
        # First try current working directory
        default_paths = [
            Path.cwd() / "scenarios.yaml",
            Path.cwd() / "scenarios.yml",
            # Then try the directory alongside the config file
            Path(__file__).parent.parent.parent / "scenarios.yaml",
        ]

        for path in default_paths:
            if path.exists():
                scenarios_path = str(path)
                break

    if scenarios_path and Path(scenarios_path).exists():
        try:
            with open(scenarios_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                user_scenarios = data.get("scenarios", {})
                print(
                    f"Info: Loaded {len(user_scenarios)} user scenarios from {scenarios_path}"
                )
                return user_scenarios
        except Exception as e:
            print(f"Warning: Failed to load user scenarios from {scenarios_path}: {e}")

    return scenarios


def merge_scenarios(
    default_scenarios: Dict[str, Any], user_scenarios: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge default scenarios and user-defined scenarios, user scenarios take precedence."""
    merged = default_scenarios.copy()
    # User scenarios will override default scenarios with the same name
    merged.update(user_scenarios)
    return merged


def load_config(
    config_path: Optional[str] = None, scenarios_path: Optional[str] = None
) -> Dict[str, Any]:
    """Load configuration from environment variables and/or YAML config file.

    Environment variables with the prefix MCP_ are automatically included
    in the configuration (with the prefix removed and name lowercased).

    Args:
        config_path: Optional path to a YAML config file
        scenarios_path: Optional path to a scenarios YAML file

    Returns:
        A dictionary containing configuration values
    """
    # Load scenario configuration
    default_scenarios = load_default_scenarios()
    user_scenarios = load_user_scenarios(scenarios_path)
    merged_scenarios = merge_scenarios(default_scenarios, user_scenarios)

    # Start with empty config
    config = {
        "server": {
            "name": "jenkins",
            "version": "0.1.0",
        },
        "servers": [],  # New: store multiple Jenkins servers
        "scenarios": merged_scenarios,  # New: merged scenario mapping config
    }

    # Load from YAML file if provided
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        _deep_merge(config, file_config)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")

    # Also check for config file path from environment
    env_config_path = os.environ.get("JENKINS_MCP_CONFIG_FILE")
    if env_config_path and env_config_path != config_path:
        try:
            with open(env_config_path, "r") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    _deep_merge(config, file_config)
        except Exception as e:
            print(f"Warning: Failed to load config file from environment: {e}")

    # Override with environment variables (convert MCP_* to config entries)
    env_config = {}
    for key, value in os.environ.items():
        if key.startswith("MCP_") and key != "MCP_CONFIG_FILE":
            config_key_parts = key[4:].lower().split("__")
            current = env_config
            for part in config_key_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            value = _convert_value(value)
            current[config_key_parts[-1]] = value
    _deep_merge(config, env_config)
    return config


def get_jenkins_servers(config: Optional[Dict[str, Any]] = None) -> list:
    """Get all Jenkins server configs, only supports new format (servers/uri/tokenEnv)."""
    if config is None:
        config = load_config()
    servers = config.get("servers", [])
    result = []
    for s in servers:
        name = s.get("name")
        uri = s.get("uri")
        user = s.get("user")
        token = s.get("token")
        token_env = s.get("tokenEnv")
        if token_env:
            token_env_val = os.environ.get(token_env)
            if token_env_val:
                token = token_env_val
        result.append({"name": name, "uri": uri, "user": user, "token": token})
    return result


def add_jenkins_server(server: dict, config_path: str) -> None:
    """Dynamically add a Jenkins server to the YAML config file."""
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f) or {}
    else:
        file_config = {}
    servers = file_config.get("jenkins_servers", [])
    servers.append(server)
    file_config["jenkins_servers"] = servers
    with open(config_file, "w") as f:
        yaml.safe_dump(file_config, f)


def remove_jenkins_server(server_name: str, config_path: str) -> None:
    """Dynamically remove a Jenkins server (matched by name)."""
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f) or {}
        servers = file_config.get("jenkins_servers", [])
        servers = [s for s in servers if s.get("name") != server_name]
        file_config["jenkins_servers"] = servers
        with open(config_file, "w") as f:
            yaml.safe_dump(file_config, f)


def get_scenario_mapping(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get scenario mapping config."""
    if config is None:
        config = load_config()
    return config.get("scenarios", {})


def add_scenario_mapping(
    scenario_name: str, scenario_config: dict, config_path: str
) -> None:
    """Dynamically add scenario mapping config to YAML config file."""
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f) or {}
    else:
        file_config = {}
    scenarios = file_config.get("scenarios", {})
    scenarios[scenario_name] = scenario_config
    file_config["scenarios"] = scenarios
    with open(config_file, "w") as f:
        yaml.safe_dump(file_config, f)


def remove_scenario_mapping(scenario_name: str, config_path: str) -> None:
    """Dynamically remove scenario mapping config (matched by name)."""
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            file_config = yaml.safe_load(f) or {}
        scenarios = file_config.get("scenarios", {})
        if scenario_name in scenarios:
            del scenarios[scenario_name]
        file_config["scenarios"] = scenarios
        with open(config_file, "w") as f:
            yaml.safe_dump(file_config, f)


def _convert_value(value: str) -> Any:
    """Try to convert a string value to an appropriate type.

    Args:
        value: The string value to convert

    Returns:
        The converted value
    """
    # Handle booleans
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False

    # Handle null
    if value.lower() in ("null", "none"):
        return None

    # Handle numbers
    try:
        # Try as int
        return int(value)
    except ValueError:
        try:
            # Try as float
            return float(value)
        except ValueError:
            # Keep as string
            return value


def _deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Deep merge two dictionaries.

    Args:
        target: The target dictionary to merge into
        source: The source dictionary to merge from
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            _deep_merge(target[key], value)
        else:
            # Otherwise, simply overwrite the value
            target[key] = value
