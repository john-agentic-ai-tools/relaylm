from typing import Any

try:
    from huggingface_hub import HfApi

    _api: HfApi | None = HfApi()
except ImportError:
    _api = None


def query_available_models(
    task: str = "text-generation",
    library: str | None = "vllm",
    limit: int = 20,
) -> list[dict[str, Any]]:
    if _api is None:
        return _fallback_model_list()

    try:
        models = _api.list_models(
            task=task,
            library=library,
            sort="downloads",
            direction=-1,
            limit=limit,
        )
        result = []
        for m in models:
            result.append(
                {
                    "id": m.id,
                    "pipeline_tag": m.pipeline_tag,
                    "downloads": getattr(m, "downloads", 0),
                    "library": library,
                }
            )
        return result
    except Exception:
        return _fallback_model_list()


def _fallback_model_list() -> list[dict[str, Any]]:
    return [
        {
            "id": "Qwen/Qwen3-0.6B",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "library": "vllm",
        },
        {
            "id": "Qwen/Qwen3-1.5B",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "library": "vllm",
        },
        {
            "id": "Qwen/Qwen3-4B",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "library": "vllm",
        },
        {
            "id": "mistralai/Mistral-7B-Instruct-v0.3",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "library": "vllm",
        },
        {
            "id": "meta-llama/Llama-3.1-8B",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "library": "vllm",
        },
    ]


def get_model_info(model_id: str) -> dict[str, Any] | None:
    if _api is None:
        return None
    try:
        info = _api.model_info(model_id)
        return {
            "id": info.id,
            "pipeline_tag": info.pipeline_tag,
            "disabled": getattr(info, "disabled", False),
            "library": getattr(info, "library_name", None),
        }
    except Exception:
        return None
