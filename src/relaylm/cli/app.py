import getpass
import os
import sys
import time
from typing import Any

import typer

app = typer.Typer(
    name="relaylm",
    help="Single-command AI router environment bootstrap",
    no_args_is_help=True,
)


_PROGRESS_THROTTLE_SECONDS = 5.0
_WAIT_LOG_MAX_CHARS = 90
_last_progress_emit = 0.0


def _print_pull_progress(done: int, total: int, elapsed: float) -> None:
    global _last_progress_emit
    mins, secs = divmod(int(elapsed), 60)
    total_str = str(total) if total else "?"
    msg = f"  Pulling layers: {done}/{total_str} (elapsed {mins}m{secs:02d}s)"
    if sys.stdout.isatty():
        typer.echo(f"\r{msg}", nl=False)
        return
    if elapsed - _last_progress_emit >= _PROGRESS_THROTTLE_SECONDS:
        typer.echo(msg)
        _last_progress_emit = elapsed


def _print_wait_progress(elapsed: float, last_log: str | None) -> None:
    global _last_progress_emit
    mins, secs = divmod(int(elapsed), 60)
    snippet = (last_log or "starting up...").strip()
    if len(snippet) > _WAIT_LOG_MAX_CHARS:
        snippet = snippet[: _WAIT_LOG_MAX_CHARS - 1] + "…"
    msg = f"  Waiting for vLLM ({mins}m{secs:02d}s) | {snippet}"
    if sys.stdout.isatty():
        typer.echo(f"\r\033[K{msg}", nl=False)
        return
    if elapsed - _last_progress_emit >= _PROGRESS_THROTTLE_SECONDS:
        typer.echo(msg)
        _last_progress_emit = elapsed


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
    from relaylm.platform import is_wsl2, wsl_distro_name

    on_wsl2 = is_wsl2()
    if on_wsl2:
        typer.echo(f"Detected WSL2 distro: {wsl_distro_name() or 'unknown'}")

    hardware = detect()
    typer.echo(f"Detected hardware: {hardware}")
    if on_wsl2 and not hardware.has_nvidia_gpu:
        typer.echo(
            "Note: no NVIDIA GPU detected under WSL2. If you have an NVIDIA GPU, "
            "install the Windows-side NVIDIA CUDA on WSL driver and verify "
            "`nvidia-smi` works inside this distro."
        )

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
        wsl_hint = (
            " On WSL2: enable Docker Desktop's WSL integration for this distro, "
            "or run `sudo apt install podman` inside the distro."
            if on_wsl2
            else ""
        )
        if yes:
            typer.echo(
                "No container runtime found. Install Podman: "
                "https://podman.io/docs/installation" + wsl_hint
            )
            raise typer.Exit(code=1)
        typer.echo("No container runtime detected." + wsl_hint)
        if typer.confirm("Install Podman now?"):
            typer.echo("Installing Podman... (platform-specific)")
        else:
            raise typer.Exit(code=1)

    typer.echo(f"Using container runtime: {rt}")

    from relaylm.container.vllm import VLLM_IMAGE, VLLMManager

    manager = VLLMManager(runtime=rt)
    use_gpu = hardware.has_nvidia_gpu or hardware.has_amd_gpu

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token and not yes:
        typer.echo(
            "Hugging Face token not set. A token enables higher download "
            "rate limits and access to gated models "
            "(see https://huggingface.co/settings/tokens). Press Enter to skip."
        )
        entered = getpass.getpass("HF_TOKEN (hidden, optional): ").strip()
        hf_token = entered or None
    if hf_token:
        typer.echo("Using HF_TOKEN for Hugging Face authentication.")
    else:
        typer.echo(
            "No HF_TOKEN set — downloads will be unauthenticated and rate-limited. "
            "Set HF_TOKEN in your environment to authenticate."
        )

    typer.echo("Checking for existing vLLM container...")

    def _confirm(prompt: str) -> bool:
        return typer.confirm(prompt, default=False)

    global _last_progress_emit

    def _pull_progress(done: int, total: int, elapsed: float) -> None:
        # The first time we get a progress callback, announce the pull.
        global _last_progress_emit
        if _last_progress_emit == 0.0 and elapsed < 1.0:
            typer.echo(
                f"Pulling vLLM image ({VLLM_IMAGE}, ~10 GB). "
                "First pull can take 10-30 minutes depending on your connection."
            )
        _print_pull_progress(done, total, elapsed)

    _last_progress_emit = 0.0
    try:
        container_id, reused = manager.reconcile(
            model_names=[m["name"] for m in selected_models],
            gpu=use_gpu,
            hf_token=hf_token,
            assume_yes=yes,
            confirm=_confirm,
            on_pull_progress=_pull_progress,
        )
    except RuntimeError as exc:
        if sys.stdout.isatty():
            typer.echo("")
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if sys.stdout.isatty() and _last_progress_emit != 0.0:
        typer.echo("")

    if reused:
        typer.echo(f"Reusing existing vLLM container: {container_id}")
    else:
        typer.echo(f"vLLM container started: {container_id}")

    from relaylm.container.runtime import container_status

    typer.echo(
        "Waiting for vLLM to load models (this can take 5-15 minutes on first run)..."
    )
    _last_progress_emit = 0.0
    ready_start = time.monotonic()
    ready = manager.wait_until_ready(
        timeout=900.0,
        container_id=container_id,
        on_tick=_print_wait_progress,
    )
    if sys.stdout.isatty():
        typer.echo("")
    if not ready:
        status = container_status(rt, container_id)
        if status in ("exited", "dead"):
            typer.echo(
                f"vLLM container exited during startup (status: {status}). "
                f"Check logs: `{rt} logs {container_id}`",
                err=True,
            )
        else:
            typer.echo(
                f"Router did not become ready within 15 minutes. "
                f"Check container logs: `{rt} logs {container_id}`",
                err=True,
            )
        raise typer.Exit(code=1)
    ready_elapsed = int(time.monotonic() - ready_start)
    typer.echo(
        f"Router ready at {manager.endpoint_url} "
        f"(took {ready_elapsed // 60}m{ready_elapsed % 60:02d}s)"
    )

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
