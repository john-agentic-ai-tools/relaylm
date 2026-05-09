from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path.home() / ".config" / "relaylm"
CONFIG_PATH = CONFIG_DIR / "config.yml"


def get_config_path() -> Path:
    return CONFIG_PATH


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        result = yaml.safe_load(f)
        return result if isinstance(result, dict) else {}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "version" not in config:
        errors.append("Missing required field: version")
    runtime = config.get("container_runtime")
    if runtime and runtime not in ("podman", "docker"):
        errors.append(f"container_runtime must be 'podman' or 'docker', got: {runtime}")
    models = config.get("models", [])
    for i, m in enumerate(models):
        if not m.get("name"):
            errors.append(f"models[{i}].name is required")
    fallback = config.get("fallback", {})
    order = fallback.get("order", [])
    if (
        order
        and "local" not in order
        and not any(p in order for p in ("anthropic", "openai"))
    ):
        errors.append("fallback.order must include at least one valid target")
    return errors
