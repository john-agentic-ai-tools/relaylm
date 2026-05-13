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
from relaylm.models.registry import ModelSpec

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

# Tuning constants for auto-sized memory args.
_UTIL_MIN = 0.70
_UTIL_MAX = 0.95
_UTIL_HEADROOM = 0.95  # use 95% of free / total ratio (never 100%)
_MAX_MODEL_LEN_CAP = 8192  # hard ceiling so we don't reserve absurd KV space
_DEFAULT_MAX_NUM_SEQS = 1


@dataclass
class VLLMOverrides:
    """Power-user overrides for the auto-computed memory args."""

    gpu_memory_utilization: float | None = None
    max_model_len: int | None = None
    max_num_seqs: int | None = None


@dataclass
class ResolvedVLLMArgs:
    """Result of `build_vllm_args` — the flags plus the inputs we used."""

    args: list[str]
    util: float
    max_model_len: int
    max_num_seqs: int
    weights_gb: float
    overhead_gb: float
    kv_budget_gb: float


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def build_vllm_args(
    specs: list[ModelSpec],
    *,
    total_vram_gb: float,
    free_vram_gb: float,
    overrides: VLLMOverrides | None = None,
) -> ResolvedVLLMArgs:
    """Compute vLLM CLI flags from selected model(s) + measured VRAM.

    The primary model (specs[0]) drives the memory math; additional
    models are loaded into the same budget at vLLM's discretion.
    """
    if not specs:
        raise ValueError("build_vllm_args requires at least one ModelSpec")
    overrides = overrides or VLLMOverrides()
    primary = specs[0]

    if overrides.gpu_memory_utilization is not None:
        util = float(overrides.gpu_memory_utilization)
    elif total_vram_gb > 0:
        util = _clamp(
            (free_vram_gb / total_vram_gb) * _UTIL_HEADROOM, _UTIL_MIN, _UTIL_MAX
        )
    else:
        util = _UTIL_MIN
    util = round(util, 2)

    budget_gb = total_vram_gb * util
    kv_budget_gb = max(0.0, budget_gb - primary.weights_gb - primary.overhead_gb)
    if overrides.max_model_len is not None:
        max_model_len = int(overrides.max_model_len)
    elif primary.kv_bytes_per_token > 0 and kv_budget_gb > 0:
        auto_len = int(kv_budget_gb * 1e9 / primary.kv_bytes_per_token)
        max_model_len = min(auto_len, _MAX_MODEL_LEN_CAP)
        # Floor to a sensible minimum so we either succeed or fall back early.
        max_model_len = max(512, max_model_len)
    else:
        max_model_len = 2048

    max_num_seqs = (
        int(overrides.max_num_seqs)
        if overrides.max_num_seqs is not None
        else _DEFAULT_MAX_NUM_SEQS
    )

    args: list[str] = ["--model", primary.name]
    for s in specs[1:]:
        args.extend(["--model", s.name])
    args.extend(
        [
            "--gpu-memory-utilization",
            f"{util:.2f}",
            "--max-model-len",
            str(max_model_len),
            "--max-num-seqs",
            str(max_num_seqs),
            "--enforce-eager",
        ]
    )
    return ResolvedVLLMArgs(
        args=args,
        util=util,
        max_model_len=max_model_len,
        max_num_seqs=max_num_seqs,
        weights_gb=primary.weights_gb,
        overhead_gb=primary.overhead_gb,
        kv_budget_gb=kv_budget_gb,
    )


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
        specs: list[ModelSpec],
        *,
        gpu: bool = False,
        total_vram_gb: float,
        free_vram_gb: float,
        overrides: VLLMOverrides | None = None,
        hf_token: str | None = None,
    ) -> tuple[str, ResolvedVLLMArgs]:
        """Launch the vLLM container (detached).

        Returns (container_id, resolved_args). `resolved_args` carries the
        memory breakdown the CLI may want to echo.
        """
        env = {"HF_HOME": "/root/.cache/huggingface"}
        if hf_token:
            env["HF_TOKEN"] = hf_token
        volume = f"{Path.home() / '.cache' / 'huggingface'}:/root/.cache/huggingface"
        resolved = build_vllm_args(
            specs,
            total_vram_gb=total_vram_gb,
            free_vram_gb=free_vram_gb,
            overrides=overrides,
        )
        model_names = [s.name for s in specs]
        signature = compute_config_signature(
            model_names=model_names,
            gpu=gpu,
            port=LOCAL_PORT,
            image=self.image,
            extra_args=resolved.args,
        )
        labels = {MANAGED_LABEL: "true", CONFIG_LABEL: signature}

        result = run_container(
            runtime=self.runtime,
            image=self.image,
            ports={LOCAL_PORT: CONTAINER_PORT},
            volumes=[volume],
            gpu=gpu,
            env=env,
            extra_args=resolved.args,
            labels=labels,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start vLLM container: {result.stderr.strip()}"
            )
        container_id = (result.stdout or "").strip()
        self.container_id = container_id
        return container_id, resolved

    def find_existing(self) -> list[ManagedContainer]:
        rows = list_managed_containers(self.runtime)
        return [ManagedContainer(id=i, status=s, signature=g) for i, s, g in rows]

    def reconcile(
        self,
        specs: list[ModelSpec],
        *,
        gpu: bool = False,
        total_vram_gb: float,
        free_vram_gb: float,
        overrides: VLLMOverrides | None = None,
        hf_token: str | None = None,
        assume_yes: bool = False,
        confirm: ConfirmFn | None = None,
        on_pull_progress: PullProgress | None = None,
    ) -> tuple[str, bool, ResolvedVLLMArgs]:
        """Reuse a matching running container or stop+recreate.

        Returns (container_id, reused, resolved_args). On reuse, image
        pull and container creation are skipped entirely. On recreate,
        ensure_image runs and the new container is started. Raises
        RuntimeError if the user declines a needed recreate.
        """
        resolved = build_vllm_args(
            specs,
            total_vram_gb=total_vram_gb,
            free_vram_gb=free_vram_gb,
            overrides=overrides,
        )
        desired_sig = compute_config_signature(
            model_names=[s.name for s in specs],
            gpu=gpu,
            port=LOCAL_PORT,
            image=self.image,
            extra_args=resolved.args,
        )
        existing = self.find_existing()

        match = next(
            (
                c
                for c in existing
                if c.status == "running" and c.signature == desired_sig
            ),
            None,
        )
        if match is not None:
            for c in existing:
                if c.id != match.id:
                    self.shutdown(c.id)
            self.container_id = match.id
            return (match.id, True, resolved)

        running_mismatch = [
            c for c in existing if c.status == "running" and c.signature != desired_sig
        ]
        if running_mismatch and not assume_yes:
            allowed = (
                confirm(
                    "Existing vLLM container has different config "
                    "(models / gpu / port / tuning). Recreate? [y/N]"
                )
                if confirm is not None
                else False
            )
            if not allowed:
                raise RuntimeError(
                    "Refusing to recreate running vLLM container without confirmation. "
                    "Pass --yes, or stop the existing container manually."
                )

        for c in existing:
            self.shutdown(c.id)

        self.ensure_image(on_progress=on_pull_progress)
        new_id, _ = self.start_container(
            specs,
            gpu=gpu,
            total_vram_gb=total_vram_gb,
            free_vram_gb=free_vram_gb,
            overrides=overrides,
            hf_token=hf_token,
        )
        return (new_id, False, resolved)

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

    def shutdown(self, container_id: str) -> None:
        stop_container(self.runtime, container_id)
        remove_container(self.runtime, container_id)

    @property
    def endpoint_url(self) -> str:
        return f"http://127.0.0.1:{LOCAL_PORT}/v1"
