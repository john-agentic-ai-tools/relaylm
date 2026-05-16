import getpass
import os
import sys
import time
from typing import Any

import typer


def _version_callback(value: bool) -> None:
    if value:
        from relaylm._buildinfo import version_string

        typer.echo(version_string())
        raise typer.Exit()


app = typer.Typer(
    name="relaylm",
    help="Single-command AI router environment bootstrap",
    no_args_is_help=True,
)


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "-v",
        "--version",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


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
    max_model_len: int | None = typer.Option(
        None,
        "--max-model-len",
        help="Advanced: override the auto-computed vLLM max-model-len.",
    ),
    max_num_seqs: int | None = typer.Option(
        None,
        "--max-num-seqs",
        help="Advanced: override the default vLLM max-num-seqs (default 1).",
    ),
    gpu_memory_util: float | None = typer.Option(
        None,
        "--gpu-memory-util",
        help="Advanced: override the auto-computed vLLM gpu-memory-utilization.",
    ),
) -> None:
    """Bootstrap the local AI routing environment."""
    from relaylm.config.backup import create_backup
    from relaylm.config.loader import load_config, save_config
    from relaylm.container.runtime import detect_runtime
    from relaylm.hardware.detector import detect
    from relaylm.models.registry import find as find_spec
    from relaylm.models.selector import (
        resolve_specs,
        select_model,
        validate_models,
    )
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
        selected_specs = resolve_specs(model_list)
        for name, spec in zip(model_list, selected_specs):
            if find_spec(name) is None:
                typer.echo(
                    f"Warning: '{name}' is not in the curated registry. "
                    f"Auto-sizing will use heuristic estimates "
                    f"(~{spec.params_b:.1f}B FP16). Pass --max-model-len / "
                    f"--gpu-memory-util to tune if needed."
                )
    else:
        chosen = select_model(hardware)
        if chosen is None:
            free_gb = hardware.max_gpu_vram_free_gb
            total_gb = hardware.max_gpu_vram_gb
            typer.echo(
                f"No local model fits your available VRAM "
                f"({free_gb:.1f} GB free of {total_gb:.1f} GB total).\n"
                "Configure a cloud provider to use cloud inference instead:\n"
                "  relaylm providers add anthropic --key sk-ant-...\n"
                "  relaylm providers add openai    --key sk-...",
                err=True,
            )
            raise typer.Exit(code=1)
        selected_specs = [chosen]
    # Mirror in config-entry shape for save_config below.
    selected_models: list[dict[str, Any]] = [
        {"name": s.name, "source": "huggingface", "gpu_index": None, "args": {}}
        for s in selected_specs
    ]

    typer.echo(f"Selected models: {[s.name for s in selected_specs]}")
    primary = selected_specs[0]
    typer.echo(
        f"  weights: {primary.weights_gb:.1f} GB ({primary.params_b}B params, "
        f"{primary.dtype})"
    )

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

    from relaylm.container.vllm import VLLM_IMAGE, VLLMManager, VLLMOverrides

    manager = VLLMManager(runtime=rt)
    use_gpu = hardware.has_nvidia_gpu or hardware.has_amd_gpu
    overrides = VLLMOverrides(
        gpu_memory_utilization=gpu_memory_util,
        max_model_len=max_model_len,
        max_num_seqs=max_num_seqs,
    )
    total_vram_gb = hardware.max_gpu_vram_gb
    free_vram_gb = hardware.max_gpu_vram_free_gb

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
        container_id, reused, resolved = manager.reconcile(
            specs=selected_specs,
            gpu=use_gpu,
            total_vram_gb=total_vram_gb,
            free_vram_gb=free_vram_gb,
            overrides=overrides,
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

    if total_vram_gb > 0:
        typer.echo(
            f"GPU budget: {resolved.util * total_vram_gb:.2f} GB "
            f"({int(resolved.util * 100)}% of {total_vram_gb:.1f} GB total, "
            f"{free_vram_gb:.1f} GB free)"
        )
        typer.echo(
            f"Runtime allocation: weights {resolved.weights_gb:.1f} GB + "
            f"overhead {resolved.overhead_gb:.1f} GB + "
            f"KV cache up to {resolved.kv_budget_gb:.1f} GB"
        )
    typer.echo(
        f"Auto-tuned: --max-model-len {resolved.max_model_len} "
        f"--max-num-seqs {resolved.max_num_seqs} "
        f"--gpu-memory-utilization {resolved.util:.2f}"
    )

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

    from relaylm.agents.detector import run_autoconfig

    autoconfig_result = run_autoconfig()
    typer.echo(autoconfig_result.summary)

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
def info() -> None:
    """Print runtime/build info — version, package location, git SHA, platform."""
    from relaylm._buildinfo import runtime_info

    rt = runtime_info()
    width = max(len(k) for k in rt)
    for key, val in rt.items():
        typer.echo(f"  {key:<{width}}  {val}")


autoconfig_app = typer.Typer(
    help="Auto-detect and configure supported coding agents (OpenCode, Claude Code)."
)
app.add_typer(autoconfig_app, name="autoconfig")


@autoconfig_app.callback(invoke_without_command=True)
def autoconfig(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Scan and report what would change without writing"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "--non-interactive",
        help="Skip confirmation prompt, apply changes immediately",
    ),
) -> None:
    from relaylm.agents.detector import run_autoconfig

    if ctx.invoked_subcommand is not None:
        return

    try:
        if dry_run:
            result = run_autoconfig(dry_run=True)
            typer.echo(result.summary)
            return

        if not yes:
            preview = run_autoconfig(dry_run=True)
            typer.echo(preview.summary)

            if not any(a.detected for a in preview.agents):
                return

            if not sys.stdin.isatty():
                typer.echo(
                    "\nRefusing to apply changes without confirmation. "
                    "Re-run with --yes to skip the prompt.",
                    err=True,
                )
                raise typer.Exit(code=1)

            if not typer.confirm("\nApply these changes?", default=True):
                typer.echo("Aborted. No changes made.")
                return

        result = run_autoconfig()
        typer.echo(result.summary)

    except PermissionError:
        typer.echo(
            "Error: Could not write config. "
            "Check write permissions on ~/.config/relaylm/",
            err=True,
        )
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Error during autoconfig: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@autoconfig_app.command()
def revert() -> None:
    """Restore relaylm config from the most recent autoconfig backup."""
    from relaylm.agents.detector import revert_autoconfig

    result = revert_autoconfig()
    if result.success:
        typer.echo(result.message)
        return
    typer.echo(result.message, err=True)
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
