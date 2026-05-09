from pathlib import Path

from relaylm.container.runtime import (
    detect_runtime,
    pull_image,
    remove_container,
    run_container,
    stop_container,
)

VLLM_IMAGE = "vllm/vllm-openai:latest"
VLLM_IMAGE_ROCM = "vllm/vllm-openai-rocm:latest"
LOCAL_PORT = 8000
CONTAINER_PORT = 8000


class VLLMManager:
    def __init__(self, runtime: str | None = None):
        detected = runtime or detect_runtime()
        if detected is None:
            raise RuntimeError("No container runtime found (install Podman or Docker)")
        self.runtime: str = detected

    def deploy(self, model_names: list[str], gpu: bool = False) -> str:
        image = VLLM_IMAGE
        env = {"HF_HOME": "/root/.cache/huggingface"}

        pull_image(self.runtime, image)

        volume = f"{Path.home() / '.cache' / 'huggingface'}:/root/.cache/huggingface"
        args = ["--model", model_names[0]]
        for m in model_names[1:]:
            args.extend(["--model", m])

        result = run_container(
            runtime=self.runtime,
            image=image,
            ports={LOCAL_PORT: CONTAINER_PORT},
            volumes=[volume],
            gpu=gpu,
            env=env,
            extra_args=args,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start vLLM container: {result.stderr.strip()}"
            )
        container_id: str = (result.stdout or "").strip()
        return container_id

    def shutdown(self, container_id: str) -> None:
        stop_container(self.runtime, container_id)
        remove_container(self.runtime, container_id)

    @property
    def endpoint_url(self) -> str:
        return f"http://127.0.0.1:{LOCAL_PORT}/v1"
