import shutil
import subprocess
import time
from collections.abc import Callable

PullProgress = Callable[[int, int, float], None]


def detect_runtime() -> str | None:
    podman_path = shutil.which("podman")
    docker_path = shutil.which("docker")

    if podman_path:
        try:
            result = subprocess.run(
                [podman_path, "info"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "podman"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    if docker_path:
        try:
            result = subprocess.run(
                [docker_path, "info"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "docker"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return None


def _runtime_binary(runtime: str) -> str:
    return runtime  # "podman" or "docker"


def image_exists(runtime: str, image: str) -> bool:
    """Return True if the image is already present in the local store."""
    try:
        result = subprocess.run(
            [_runtime_binary(runtime), "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_container(
    runtime: str,
    image: str,
    ports: dict[int, int] | None = None,
    volumes: list[str] | None = None,
    gpu: bool = False,
    env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
    labels: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [_runtime_binary(runtime), "run", "-d", "--ipc=host"]
    if ports:
        for host_port, container_port in ports.items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])
    if volumes:
        for v in volumes:
            cmd.extend(["-v", v])
    if gpu and runtime == "docker":
        cmd.extend(["--gpus", "all"])
    elif gpu and runtime == "podman":
        cmd.extend(["--device", "nvidia.com/gpu=all"])
    if labels:
        for k, v in labels.items():
            cmd.extend(["--label", f"{k}={v}"])
    if env:
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])
    cmd.append(image)
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def list_managed_containers(
    runtime: str, label: str = "relaylm.managed=true"
) -> list[tuple[str, str, str]]:
    """List managed containers as (id, status, config_signature) tuples.

    Best-effort: returns [] on any subprocess error.
    """
    fmt = '{{.ID}}|{{.State}}|{{.Label "relaylm.config"}}'
    try:
        result = subprocess.run(
            [
                _runtime_binary(runtime),
                "ps",
                "-a",
                "--filter",
                f"label={label}",
                "--format",
                fmt,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        out: list[tuple[str, str, str]] = []
        for raw in result.stdout.splitlines():
            parts = raw.strip().split("|")
            if len(parts) < 3 or not parts[0]:
                continue
            out.append((parts[0], parts[1], parts[2]))
        return out
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def pull_image(
    runtime: str,
    image: str,
    progress: PullProgress | None = None,
) -> int:
    """Stream `<runtime> pull <image>` and report parsed progress.

    Yields (done, total, elapsed_seconds) to `progress` whenever a recognised
    layer-progress line is observed. No hard timeout — pulls of multi-GB
    images legitimately take 10-30 minutes. Caller handles non-zero returns.
    """
    cmd = [_runtime_binary(runtime), "pull", image]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    total = 0
    done = 0
    start = time.monotonic()
    if proc.stdout is not None:
        for raw in proc.stdout:
            line = raw.rstrip()
            changed = False
            if "Pulling fs layer" in line or line.startswith("Copying blob "):
                total += 1
                changed = True
            elif (
                "Pull complete" in line
                or "Already exists" in line
                or line.startswith("Copying config ")
                or "Writing manifest" in line
            ):
                done += 1
                changed = True
            if changed and progress is not None:
                progress(done, total, time.monotonic() - start)

    return proc.wait()


def container_status(runtime: str, container_id: str) -> str:
    """Return the container's state (`running`, `exited`, ...) or `unknown`."""
    try:
        result = subprocess.run(
            [
                _runtime_binary(runtime),
                "inspect",
                "--format",
                "{{.State.Status}}",
                container_id,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "unknown"
        return "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def tail_logs(runtime: str, container_id: str, lines: int = 1) -> str:
    """Return the last non-empty log line from the container, or `""`.

    Best-effort: any error returns an empty string. vLLM writes startup
    chatter to stderr, so we merge it with stdout via `stderr=STDOUT`.
    """
    try:
        result = subprocess.run(
            [_runtime_binary(runtime), "logs", "--tail", str(lines), container_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return ""
        for raw in reversed(result.stdout.splitlines()):
            line = raw.strip()
            if line:
                return line
        return ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def stop_container(runtime: str, container_id: str) -> subprocess.CompletedProcess[str]:
    cmd = [_runtime_binary(runtime), "stop", container_id]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def remove_container(
    runtime: str, container_id: str
) -> subprocess.CompletedProcess[str]:
    cmd = [_runtime_binary(runtime), "rm", "-f", container_id]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
