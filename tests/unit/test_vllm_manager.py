import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from relaylm.container import vllm


@pytest.fixture
def manager() -> vllm.VLLMManager:
    return vllm.VLLMManager(runtime="docker")


class TestConstructor:
    def test_uses_explicit_runtime(self) -> None:
        m = vllm.VLLMManager(runtime="podman")
        assert m.runtime == "podman"

    def test_falls_back_to_detect(self) -> None:
        with patch.object(vllm, "detect_runtime", return_value="docker"):
            assert vllm.VLLMManager().runtime == "docker"

    def test_raises_when_no_runtime(self) -> None:
        with patch.object(vllm, "detect_runtime", return_value=None):
            with pytest.raises(RuntimeError, match="No container runtime"):
                vllm.VLLMManager()


class TestEnsureImage:
    def test_skips_pull_when_image_cached(self, manager: vllm.VLLMManager) -> None:
        with (
            patch.object(vllm, "image_exists", return_value=True),
            patch.object(vllm, "pull_image") as pull,
        ):
            assert manager.ensure_image() is True
            pull.assert_not_called()

    def test_pulls_when_image_missing(self, manager: vllm.VLLMManager) -> None:
        with (
            patch.object(vllm, "image_exists", return_value=False),
            patch.object(vllm, "pull_image", return_value=0) as pull,
        ):
            assert manager.ensure_image() is False
            pull.assert_called_once()

    def test_raises_on_pull_failure(self, manager: vllm.VLLMManager) -> None:
        with (
            patch.object(vllm, "image_exists", return_value=False),
            patch.object(vllm, "pull_image", return_value=1),
        ):
            with pytest.raises(RuntimeError, match="exit code 1"):
                manager.ensure_image()

    def test_passes_progress_callback(self, manager: vllm.VLLMManager) -> None:
        cb = MagicMock()
        with (
            patch.object(vllm, "image_exists", return_value=False),
            patch.object(vllm, "pull_image", return_value=0) as pull,
        ):
            manager.ensure_image(on_progress=cb)
        assert pull.call_args.kwargs["progress"] is cb


class TestStartContainer:
    def test_returns_container_id_on_success(self, manager: vllm.VLLMManager) -> None:
        result = MagicMock(returncode=0, stdout="cid-123\n", stderr="")
        with patch.object(vllm, "run_container", return_value=result):
            cid = manager.start_container(["model-a"], gpu=False)
        assert cid == "cid-123"
        assert manager.container_id == "cid-123"

    def test_raises_with_stderr_on_failure(self, manager: vllm.VLLMManager) -> None:
        result = MagicMock(returncode=1, stdout="", stderr="boom")
        with patch.object(vllm, "run_container", return_value=result):
            with pytest.raises(RuntimeError, match="boom"):
                manager.start_container(["model-a"])

    def test_passes_memory_safety_flags(self, manager: vllm.VLLMManager) -> None:
        # vLLM's default --gpu-memory-utilization 0.92 fails on 8 GB cards
        # when the host has other GPU users (typical on WSL2). We pass a
        # safer default and --enforce-eager to skip CUDA graph allocation.
        result = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch.object(vllm, "run_container", return_value=result) as rc:
            manager.start_container(["model-a"], gpu=True)
        extra = rc.call_args.kwargs["extra_args"]
        assert "--gpu-memory-utilization" in extra
        util_idx = extra.index("--gpu-memory-utilization")
        assert extra[util_idx + 1] == "0.85"
        assert "--enforce-eager" in extra

    def test_passes_hf_token_to_container_env(self, manager: vllm.VLLMManager) -> None:
        result = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch.object(vllm, "run_container", return_value=result) as rc:
            manager.start_container(["model-a"], hf_token="hf_secret")
        assert rc.call_args.kwargs["env"]["HF_TOKEN"] == "hf_secret"

    def test_no_hf_token_when_omitted(self, manager: vllm.VLLMManager) -> None:
        result = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch.object(vllm, "run_container", return_value=result) as rc:
            manager.start_container(["model-a"])
        assert "HF_TOKEN" not in rc.call_args.kwargs["env"]

    def test_attaches_management_labels(self, manager: vllm.VLLMManager) -> None:
        result = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch.object(vllm, "run_container", return_value=result) as rc:
            manager.start_container(["model-a"], gpu=True)
        labels = rc.call_args.kwargs["labels"]
        assert labels[vllm.MANAGED_LABEL] == "true"
        assert len(labels[vllm.CONFIG_LABEL]) == 12  # truncated sha1


class TestComputeConfigSignature:
    def _sig(self, **overrides: object) -> str:
        kwargs: dict[str, object] = {
            "model_names": ["a"],
            "gpu": False,
            "port": 8000,
            "image": "img:latest",
            "extra_args": ["--enforce-eager"],
        }
        kwargs.update(overrides)
        return vllm.compute_config_signature(**kwargs)  # type: ignore[arg-type]

    def test_deterministic(self) -> None:
        assert self._sig() == self._sig()

    def test_model_order_does_not_change_signature(self) -> None:
        assert self._sig(model_names=["a", "b"]) == self._sig(model_names=["b", "a"])

    def test_extra_args_order_does_not_change_signature(self) -> None:
        assert self._sig(extra_args=["--x", "--y"]) == self._sig(
            extra_args=["--y", "--x"]
        )

    def test_model_swap_changes_signature(self) -> None:
        assert self._sig(model_names=["a"]) != self._sig(model_names=["b"])

    def test_gpu_toggle_changes_signature(self) -> None:
        assert self._sig(gpu=False) != self._sig(gpu=True)

    def test_port_change_changes_signature(self) -> None:
        assert self._sig(port=8000) != self._sig(port=8080)

    def test_extra_arg_change_changes_signature(self) -> None:
        assert self._sig(extra_args=["--a"]) != self._sig(extra_args=["--b"])

    def test_signature_excludes_hf_token(self) -> None:
        # The function doesn't accept hf_token at all; this is a structural
        # guarantee that nothing token-shaped can leak into the hash.
        with pytest.raises(TypeError):
            vllm.compute_config_signature(  # type: ignore[call-arg]
                model_names=["a"],
                gpu=False,
                port=8000,
                image="img",
                extra_args=[],
                hf_token="hf_secret",
            )


class TestFindExisting:
    def test_returns_parsed_managed_containers(self, manager: vllm.VLLMManager) -> None:
        with patch.object(
            vllm,
            "list_managed_containers",
            return_value=[("id1", "running", "sigA"), ("id2", "exited", "sigB")],
        ):
            result = manager.find_existing()
        assert result == [
            vllm.ManagedContainer(id="id1", status="running", signature="sigA"),
            vllm.ManagedContainer(id="id2", status="exited", signature="sigB"),
        ]


class TestReconcile:
    def _patches(
        self,
        manager: vllm.VLLMManager,
        existing: list[tuple[str, str, str]],
    ) -> tuple[MagicMock, MagicMock, MagicMock]:
        # Returns (start_mock, ensure_image_mock, shutdown_mock).
        list_p = patch.object(vllm, "list_managed_containers", return_value=existing)
        list_p.start()
        start_p = patch.object(manager, "start_container", return_value="new-id")
        start_mock = start_p.start()
        ensure_p = patch.object(manager, "ensure_image", return_value=True)
        ensure_mock = ensure_p.start()
        shutdown_p = patch.object(manager, "shutdown")
        shutdown_mock = shutdown_p.start()
        return start_mock, ensure_mock, shutdown_mock

    def _matching_sig(self, model_names: list[str], gpu: bool) -> str:
        return vllm.compute_config_signature(
            model_names=model_names,
            gpu=gpu,
            port=vllm.LOCAL_PORT,
            image=vllm.VLLM_IMAGE,
            extra_args=vllm._build_vllm_args(model_names),
        )

    def test_no_existing_creates_new(self, manager: vllm.VLLMManager) -> None:
        start, ensure, shutdown = self._patches(manager, [])
        try:
            cid, reused = manager.reconcile(["m1"], gpu=False, assume_yes=True)
        finally:
            patch.stopall()
        assert (cid, reused) == ("new-id", False)
        ensure.assert_called_once()
        start.assert_called_once()
        shutdown.assert_not_called()

    def test_running_matching_signature_is_reused(
        self, manager: vllm.VLLMManager
    ) -> None:
        sig = self._matching_sig(["m1"], gpu=False)
        start, ensure, shutdown = self._patches(
            manager, [("running-id", "running", sig)]
        )
        try:
            cid, reused = manager.reconcile(["m1"], gpu=False, assume_yes=True)
        finally:
            patch.stopall()
        assert (cid, reused) == ("running-id", True)
        ensure.assert_not_called()
        start.assert_not_called()
        shutdown.assert_not_called()

    def test_running_mismatch_with_yes_recreates(
        self, manager: vllm.VLLMManager
    ) -> None:
        start, ensure, shutdown = self._patches(
            manager, [("old-id", "running", "wrong-sig")]
        )
        try:
            cid, reused = manager.reconcile(["m1"], gpu=False, assume_yes=True)
        finally:
            patch.stopall()
        assert (cid, reused) == ("new-id", False)
        shutdown.assert_called_once_with("old-id")
        ensure.assert_called_once()
        start.assert_called_once()

    def test_running_mismatch_declined_raises(self, manager: vllm.VLLMManager) -> None:
        start, ensure, shutdown = self._patches(
            manager, [("old-id", "running", "wrong-sig")]
        )
        try:
            with pytest.raises(RuntimeError, match="confirmation"):
                manager.reconcile(
                    ["m1"],
                    gpu=False,
                    assume_yes=False,
                    confirm=lambda _: False,
                )
        finally:
            patch.stopall()
        shutdown.assert_not_called()
        start.assert_not_called()
        ensure.assert_not_called()

    def test_exited_container_is_cleaned_up_then_recreated(
        self, manager: vllm.VLLMManager
    ) -> None:
        sig = self._matching_sig(["m1"], gpu=False)
        start, ensure, shutdown = self._patches(manager, [("dead-id", "exited", sig)])
        try:
            cid, reused = manager.reconcile(["m1"], gpu=False, assume_yes=True)
        finally:
            patch.stopall()
        assert (cid, reused) == ("new-id", False)
        shutdown.assert_called_once_with("dead-id")
        ensure.assert_called_once()
        start.assert_called_once()

    def test_multiple_managed_keeps_matching_running_cleans_rest(
        self, manager: vllm.VLLMManager
    ) -> None:
        sig = self._matching_sig(["m1"], gpu=False)
        start, ensure, shutdown = self._patches(
            manager,
            [
                ("keep", "running", sig),
                ("stale-exit", "exited", "other"),
                ("stale-run", "running", "other"),
            ],
        )
        try:
            cid, reused = manager.reconcile(["m1"], gpu=False, assume_yes=True)
        finally:
            patch.stopall()
        assert (cid, reused) == ("keep", True)
        ensure.assert_not_called()
        start.assert_not_called()
        # The two non-matching containers got cleaned up.
        shutdown_ids = sorted(c.args[0] for c in shutdown.call_args_list)
        assert shutdown_ids == ["stale-exit", "stale-run"]


class TestWaitUntilReady:
    def test_returns_true_on_200(self, manager: vllm.VLLMManager) -> None:
        resp = MagicMock(status=200)
        resp.__enter__ = lambda self: self
        resp.__exit__ = lambda *_: False
        with patch("urllib.request.urlopen", return_value=resp):
            assert manager.wait_until_ready(timeout=5, poll_interval=0.01) is True

    def test_returns_false_after_deadline(self, manager: vllm.VLLMManager) -> None:
        clock = {"t": 0.0}

        def fake_monotonic() -> float:
            clock["t"] += 2.0
            return clock["t"]

        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("nope"),
            ),
            patch("time.monotonic", side_effect=fake_monotonic),
            patch("time.sleep"),
        ):
            assert manager.wait_until_ready(timeout=5, poll_interval=0.01) is False

    def test_retries_on_connection_error(self, manager: vllm.VLLMManager) -> None:
        ready = MagicMock(status=200)
        ready.__enter__ = lambda self: self
        ready.__exit__ = lambda *_: False
        call_count = {"n": 0}

        def fake_urlopen(*_a: object, **_k: object) -> MagicMock:
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("not yet")
            return ready

        with (
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            patch("time.sleep"),
        ):
            assert manager.wait_until_ready(timeout=60, poll_interval=0.01) is True
        assert call_count["n"] == 3

    def test_on_tick_receives_elapsed_and_log_line(
        self, manager: vllm.VLLMManager
    ) -> None:
        ready = MagicMock(status=200)
        ready.__enter__ = lambda self: self
        ready.__exit__ = lambda *_: False
        urlopen_calls = {"n": 0}

        def fake_urlopen(*_a: object, **_k: object) -> MagicMock:
            urlopen_calls["n"] += 1
            if urlopen_calls["n"] < 3:
                raise urllib.error.URLError("not yet")
            return ready

        ticks: list[tuple[float, str | None]] = []
        log_lines = iter(["Loading config", "Loading model weights"])

        with (
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            patch.object(
                vllm, "tail_logs", side_effect=lambda *_a, **_k: next(log_lines)
            ),
            patch.object(vllm, "container_status", return_value="running"),
            patch("time.sleep"),
        ):
            ok = manager.wait_until_ready(
                timeout=60,
                poll_interval=0.01,
                container_id="cid",
                on_tick=lambda e, log: ticks.append((e, log)),
            )

        assert ok is True
        assert len(ticks) == 2
        assert ticks[0][1] == "Loading config"
        assert ticks[1][1] == "Loading model weights"

    def test_returns_false_fast_when_container_exited(
        self, manager: vllm.VLLMManager
    ) -> None:
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("nope"),
            ),
            patch.object(vllm, "tail_logs", return_value="boom"),
            patch.object(vllm, "container_status", return_value="exited") as status,
            patch("time.sleep"),
        ):
            ok = manager.wait_until_ready(
                timeout=600,
                poll_interval=0.01,
                container_id="cid",
            )

        assert ok is False
        # First tick (tick=0) hits the modulo check and finds exited → bail out.
        assert status.call_count == 1

    def test_status_check_is_throttled(self, manager: vllm.VLLMManager) -> None:
        urlopen_calls = {"n": 0}

        def fake_urlopen(*_a: object, **_k: object) -> MagicMock:
            urlopen_calls["n"] += 1
            if urlopen_calls["n"] < 7:
                raise urllib.error.URLError("not yet")
            ok = MagicMock(status=200)
            ok.__enter__ = lambda self: self
            ok.__exit__ = lambda *_: False
            return ok

        with (
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            patch.object(vllm, "tail_logs", return_value=""),
            patch.object(vllm, "container_status", return_value="running") as status,
            patch("time.sleep"),
        ):
            ok = manager.wait_until_ready(
                timeout=60,
                poll_interval=0.001,
                container_id="cid",
            )

        assert ok is True
        # Six failed polls → ticks 0..5 → status checked at ticks 0, 3 → 2 calls.
        assert status.call_count == 2
