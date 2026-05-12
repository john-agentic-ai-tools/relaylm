import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from relaylm.container.runtime import (
    PullProgress,
    container_status,
    detect_runtime,
    image_exists,
    list_managed_containers,
    pull_image,
    remove_container,
    run_container,
    stop_container,
    tail_logs,
)

WaitTick = Callable[[float, str | None], None]
ConfirmFn = Callable[[str], bool]
_EXITED_STATUSES = {"exited", "dead"}
_STATUS_CHECK_EVERY = 3  # ticks

VLLM_IMAGE = "vllm/vllm-openai:latest"
VLLM_IMAGE_ROCM = "vllm/vllm-openai-rocm:latest"
LOCAL_PORT = 8000
CONTAINER_PORT = 8000

MANAGED_LABEL = "relaylm.managed"
CONFIG_LABEL = "relaylm.config"


def _build_vllm_args(model_names: list[str]) -> list[str]:
    args = ["--model", model_names[0]]
    for m in model_names[1:]:
        args.extend(["--model", m])
    # vLLM defaults to 0.92, which fails on 8 GB cards when the host has
    # other GPU users (typical on WSL2 with a desktop session). 0.85 +
    # eager mode leaves headroom and skips CUDA graph capture.
    args.extend(["--gpu-memory-utilization", "0.85", "--enforce-eager"])
    return args


def compute_config_signature(
    *,
    model_names: list[str],
    gpu: bool,
    port: int,
    image: str,
    extra_args: list[str],
) -> str:
    """Stable 12-char SHA1 over the runtime-relevant config.

    Excludes HF_TOKEN by design — token affects only downloads, and we
    don't want secrets in Docker labels.
    """
    payload = {
        "models": sorted(model_names),
        "gpu": bool(gpu),
        "port": int(port),
        "image": image,
        "extra_args": sorted(extra_args),
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha1(blob, usedforsecurity=False).hexdigest()[:12]


@dataclass(frozen=True)
class ManagedContainer:
    id: str
    status: str
    signature: str


class VLLMManager:
    def __init__(self, runtime: str | None = None):
        detected = runtime or detect_runtime()
        if detected is None:
            raise RuntimeError("No container runtime found (install Podman or Docker)")
        self.runtime: str = detected
        self.image: str = VLLM_IMAGE
        self.container_id: str | None = None

    def image_exists(self) -> bool:
        return image_exists(self.runtime, self.image)

    def ensure_image(self, on_progress: PullProgress | None = None) -> bool:
        """Pull the vLLM image if it's not already present.

        Returns True when the image was already cached (no pull performed),
        False when a pull was performed. Raises RuntimeError on pull failure.
        """
        if self.image_exists():
            return True
        rc = pull_image(self.runtime, self.image, progress=on_progress)
        if rc != 0:
            raise RuntimeError(
                f"Failed to pull {self.image} (exit code {rc}). "
                f"Try `{self.runtime} pull {self.image}` manually for details."
            )
        return False

    def start_container(
        self,
        model_names: list[str],
        gpu: bool = False,
        hf_token: str | None = None,
    ) -> str:
        """Launch the vLLM container (detached). Returns the container ID."""
        env = {"HF_HOME": "/root/.cache/huggingface"}
        if hf_token:
            env["HF_TOKEN"] = hf_token
        volume = f"{Path.home() / '.cache' / 'huggingface'}:/root/.cache/huggingface"
        args = _build_vllm_args(model_names)
        signature = compute_config_signature(
            model_names=model_names,
            gpu=gpu,
            port=LOCAL_PORT,
            image=self.image,
            extra_args=args,
        )
        labels = {MANAGED_LABEL: "true", CONFIG_LABEL: signature}

        result = run_container(
            runtime=self.runtime,
            image=self.image,
            ports={LOCAL_PORT: CONTAINER_PORT},
            volumes=[volume],
            gpu=gpu,
            env=env,
            extra_args=args,
            labels=labels,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start vLLM container: {result.stderr.strip()}"
            )
        container_id = (result.stdout or "").strip()
        self.container_id = container_id
        return container_id

    def find_existing(self) -> list[ManagedContainer]:
        rows = list_managed_containers(self.runtime)
        return [ManagedContainer(id=i, status=s, signature=g) for i, s, g in rows]

    def reconcile(
        self,
        model_names: list[str],
        gpu: bool = False,
        hf_token: str | None = None,
        *,
        assume_yes: bool = False,
        confirm: ConfirmFn | None = None,
        on_pull_progress: PullProgress | None = None,
    ) -> tuple[str, bool]:
        """Reuse a matching running container or stop+recreate.

        Returns (container_id, reused). On reuse, image pull and container
        creation are skipped entirely. On recreate, ensure_image runs and
        the new container is started. Raises RuntimeError if the user
        declines a needed recreate.
        """
        desired_sig = compute_config_signature(
            model_names=model_names,
            gpu=gpu,
            port=LOCAL_PORT,
            image=self.image,
            extra_args=_build_vllm_args(model_names),
        )
        existing = self.find_existing()

        # Pick the running container with matching signature, if any.
        match = next(
            (
                c
                for c in existing
                if c.status == "running" and c.signature == desired_sig
            ),
            None,
        )
        if match is not None:
            # Tidy up any extra managed containers from previous runs.
            for c in existing:
                if c.id != match.id:
                    self.shutdown(c.id)
            self.container_id = match.id
            return (match.id, True)

        # Need to recreate. First, decide whether destruction is allowed.
        running_mismatch = [
            c for c in existing if c.status == "running" and c.signature != desired_sig
        ]
        if running_mismatch and not assume_yes:
            allowed = (
                confirm(
                    "Existing vLLM container has different config "
                    "(models / gpu / port). Recreate? [y/N]"
                )
                if confirm is not None
                else False
            )
            if not allowed:
                raise RuntimeError(
                    "Refusing to recreate running vLLM container without confirmation. "
                    "Pass --yes, or stop the existing container manually."
                )

        # Stop + remove every managed container we found.
        for c in existing:
            self.shutdown(c.id)

        # Pull (no-op if cached) then start fresh.
        self.ensure_image(on_progress=on_pull_progress)
        new_id = self.start_container(model_names, gpu=gpu, hf_token=hf_token)
        return (new_id, False)

    def wait_until_ready(
        self,
        timeout: float = 900.0,
        poll_interval: float = 3.0,
        container_id: str | None = None,
        on_tick: WaitTick | None = None,
    ) -> bool:
        """Poll the router's /models endpoint until it responds with HTTP 200.

        Returns True once ready, False if the deadline is exceeded or the
        container exits during startup.
        """
        url = f"{self.endpoint_url}/models"
        start = time.monotonic()
        deadline = start + timeout
        tick = 0
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except (urllib.error.URLError, ConnectionError, OSError, TimeoutError):
                pass

            elapsed = time.monotonic() - start
            last_log: str | None = None
            if container_id is not None:
                log_line = tail_logs(self.runtime, container_id, 1)
                last_log = log_line or None
            if on_tick is not None:
                on_tick(elapsed, last_log)

            if container_id is not None and tick % _STATUS_CHECK_EVERY == 0:
                status = container_status(self.runtime, container_id)
                if status in _EXITED_STATUSES:
                    return False

            tick += 1
            time.sleep(poll_interval)
        return False

    def deploy(
        self,
        model_names: list[str],
        gpu: bool = False,
        hf_token: str | None = None,
    ) -> str:
        """Convenience: pull image (if needed) and start the container.

        Kept for backward compatibility; the CLI uses the staged methods
        directly so it can interleave progress messages.
        """
        self.ensure_image()
        return self.start_container(model_names, gpu=gpu, hf_token=hf_token)

    def shutdown(self, container_id: str) -> None:
        stop_container(self.runtime, container_id)
        remove_container(self.runtime, container_id)

    @property
    def endpoint_url(self) -> str:
        return f"http://127.0.0.1:{LOCAL_PORT}/v1"
