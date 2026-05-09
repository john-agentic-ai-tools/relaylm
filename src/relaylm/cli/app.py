import getpass
from typing import Any

import typer

app = typer.Typer(
    name="relaylm",
    help="Single-command AI router environment bootstrap",
    no_args_is_help=True,
)

providers_app = typer.Typer(help="Manage external AI providers")
config_app = typer.Typer(help="Manage RelayLM configuration")
app.add_typer(providers_app, name="providers")
app.add_typer(config_app, name="config")


@app.command()
def setup(
    models: str | None = typer.Option(
        None, "--models", help="Comma-separated model list (overrides auto-detection)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "--non-interactive",
        help="Auto-accept all prompts (non-interactive mode)",
    ),
    runtime: str | None = typer.Option(
        None, "--runtime", help="Force container runtime: podman or docker"
    ),
    port: int = typer.Option(8000, "--port", help="Router port"),
) -> None:
    """Bootstrap the local AI routing environment."""
    from relaylm.config.backup import create_backup
    from relaylm.config.loader import load_config, save_config
    from relaylm.container.runtime import detect_runtime
    from relaylm.hardware.detector import detect
    from relaylm.models.selector import select_models, validate_models

    hardware = detect()
    typer.echo(f"Detected hardware: {hardware}")

    if models:
        model_list = [m.strip() for m in models.split(",")]
        invalid = validate_models(model_list)
        if invalid:
            typer.echo(f"Error: Invalid model names: {invalid}", err=True)
            raise typer.Exit(code=2)
        selected_models: list[dict[str, Any]] = [
            {"name": m, "source": "huggingface", "gpu_index": None, "args": {}}
            for m in model_list
        ]
    else:
        selected_models = select_models(hardware)

    typer.echo(f"Selected models: {[m['name'] for m in selected_models]}")

    rt = runtime or detect_runtime()
    if rt is None:
        if yes:
            typer.echo(
                "No container runtime found. Install Podman: https://podman.io/docs/installation"
            )
            raise typer.Exit(code=1)
        typer.echo("No container runtime detected.")
        if typer.confirm("Install Podman now?"):
            typer.echo("Installing Podman... (platform-specific)")
        else:
            raise typer.Exit(code=1)

    typer.echo(f"Using container runtime: {rt}")

    from relaylm.container.vllm import VLLMManager

    manager = VLLMManager(runtime=rt)
    use_gpu = hardware.has_nvidia_gpu or hardware.has_amd_gpu
    container_id = manager.deploy([m["name"] for m in selected_models], gpu=use_gpu)
    typer.echo(f"vLLM container started: {container_id}")
    typer.echo(f"Router endpoint: {manager.endpoint_url}")

    from relaylm.agents.detector import detect_and_configure_agents

    detect_and_configure_agents(manager.endpoint_url)

    create_backup()
    config = load_config()
    config["version"] = 1
    config["container_runtime"] = rt
    config["models"] = selected_models
    config.setdefault("fallback", {"order": ["local"], "timeout_seconds": 30})
    config.setdefault("router", {"host": "127.0.0.1", "port": port})
    save_config(config)

    typer.echo("Configuration saved to ~/.config/relaylm/config.yml")
    typer.echo(f"Setup complete! Router ready at {manager.endpoint_url}")


@providers_app.command()
def add(
    name: str = typer.Argument(help="Provider name: anthropic or openai"),
    key: str | None = typer.Option(
        None, "--key", help="API key (prompts securely if omitted)"
    ),
    base_url: str | None = typer.Option(None, "--base-url", help="API base URL"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation"),
) -> None:
    """Configure a new external AI provider."""
    from relaylm.config.backup import create_backup
    from relaylm.config.loader import load_config, save_config
    from relaylm.providers.keychain import store_key

    if name not in ("anthropic", "openai"):
        typer.echo(
            f"Error: provider must be 'anthropic' or 'openai', got '{name}'", err=True
        )
        raise typer.Exit(code=2)

    resolved_key = key
    if resolved_key is None and not yes:
        resolved_key = getpass.getpass(f"Enter {name} API key: ")

    if resolved_key is None:
        typer.echo(
            "Error: API key is required (use --key or enter when prompted)", err=True
        )
        raise typer.Exit(code=2)

    store_key(f"relaylm-{name}", resolved_key)
    typer.echo(f"API key for {name} stored securely.")

    create_backup()
    config = load_config()
    config.setdefault("providers", {})
    provider_entry = config["providers"].setdefault(name, {})
    provider_entry["enabled"] = True
    provider_entry["base_url"] = base_url or (
        "https://api.anthropic.com/v1"
        if name == "anthropic"
        else "https://api.openai.com/v1"
    )
    provider_entry["keychain_service"] = f"relaylm-{name}"
    fallback = config.setdefault(
        "fallback", {"order": ["local"], "timeout_seconds": 30}
    )
    if name not in fallback.get("order", []):
        fallback.setdefault("order", ["local"]).append(name)
    save_config(config)
    typer.echo(f"Provider '{name}' configured.")


@providers_app.command()
def list_cmd() -> None:
    """List configured providers."""
    from relaylm.providers.manager import ProviderManager

    mgr = ProviderManager()
    providers = mgr.list_providers()
    if not providers:
        typer.echo("No providers configured.")
        return
    for p in providers:
        key_status = "key set" if p["has_key"] else "no key"
        typer.echo(f"  {p['name']}: enabled={p['enabled']}, {key_status}")


@config_app.command()
def show() -> None:
    """Print current configuration (secrets masked)."""
    from relaylm.config.loader import load_config

    config = load_config()
    if not config:
        typer.echo("No configuration found. Run 'relaylm setup' first.")
        raise typer.Exit(code=1)
    typer.echo(config)


@config_app.command()
def path() -> None:
    """Print the configuration file path."""
    from relaylm.config.loader import get_config_path

    typer.echo(str(get_config_path()))


@config_app.command()
def restore(
    timestamp: str | None = typer.Argument(None, help="Backup timestamp to restore"),
    list_backups: bool = typer.Option(False, "--list", help="List available backups"),
) -> None:
    """Restore configuration from a backup."""
    from relaylm.config.backup import list_backups as get_backups
    from relaylm.config.backup import restore_backup

    if list_backups:
        backups = get_backups()
        if not backups:
            typer.echo("No backups found.")
            return
        for b in backups:
            typer.echo(f"  {b['timestamp']}")
        return

    if timestamp is None:
        typer.echo(
            "Specify a timestamp or use --list to see available backups.", err=True
        )
        raise typer.Exit(code=2)

    result = restore_backup(timestamp)
    if result is None:
        typer.echo(f"Backup '{timestamp}' not found.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Configuration restored from backup '{timestamp}'.")


@app.command()
def agents(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be changed without writing"
    ),
    yes: bool = typer.Option(False, "--yes", help="Apply changes without confirmation"),
) -> None:
    """Detect and configure coding agents."""
    from relaylm.agents.detector import detect_and_configure_agents

    endpoint = "http://127.0.0.1:8000/v1"
    detect_and_configure_agents(endpoint, dry_run=dry_run)


if __name__ == "__main__":
    app()
