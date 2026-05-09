import shutil
import subprocess


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


def run_container(
    runtime: str,
    image: str,
    ports: dict[int, int] | None = None,
    volumes: list[str] | None = None,
    gpu: bool = False,
    env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
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
    if env:
        for k, v in env.items():
            cmd.extend(["-e", f"{k}={v}"])
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend([image])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def pull_image(runtime: str, image: str) -> subprocess.CompletedProcess[str]:
    cmd = [_runtime_binary(runtime), "pull", image]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def stop_container(runtime: str, container_id: str) -> subprocess.CompletedProcess[str]:
    cmd = [_runtime_binary(runtime), "stop", container_id]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def remove_container(
    runtime: str, container_id: str
) -> subprocess.CompletedProcess[str]:
    cmd = [_runtime_binary(runtime), "rm", "-f", container_id]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
