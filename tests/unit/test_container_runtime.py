import subprocess
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from relaylm.container import runtime


class TestImageExists:
    def test_returns_true_when_inspect_succeeds(self) -> None:
        completed = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=completed) as run:
            assert runtime.image_exists("docker", "img:tag") is True
        cmd = run.call_args.args[0]
        assert cmd == ["docker", "image", "inspect", "img:tag"]

    def test_returns_false_when_inspect_fails(self) -> None:
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert runtime.image_exists("docker", "missing") is False

    def test_returns_false_when_binary_missing(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert runtime.image_exists("docker", "img") is False

    def test_returns_false_on_timeout(self) -> None:
        err = subprocess.TimeoutExpired(cmd="docker", timeout=10)
        with patch("subprocess.run", side_effect=err):
            assert runtime.image_exists("docker", "img") is False


def _popen_with_lines(lines: list[str], returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    body = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
    proc.stdout = StringIO(body)
    proc.wait.return_value = returncode
    return proc


class TestPullImage:
    def test_parses_docker_progress_lines(self) -> None:
        lines = [
            "abc: Pulling fs layer",
            "def: Pulling fs layer",
            "ghi: Pulling fs layer",
            "abc: Already exists",
            "def: Pull complete",
            "ghi: Pull complete",
            "Status: Downloaded newer image",
        ]
        proc = _popen_with_lines(lines, returncode=0)
        calls: list[tuple[int, int]] = []

        def cb(done: int, total: int, _elapsed: float) -> None:
            calls.append((done, total))

        with patch("subprocess.Popen", return_value=proc):
            rc = runtime.pull_image("docker", "img:tag", progress=cb)

        assert rc == 0
        assert calls == [
            (0, 1),
            (0, 2),
            (0, 3),
            (1, 3),
            (2, 3),
            (3, 3),
        ]

    def test_parses_podman_progress_lines(self) -> None:
        lines = [
            "Copying blob 1234abcd",
            "Copying blob 5678efgh",
            "Copying config aabbccdd",
            "Writing manifest to image destination",
        ]
        proc = _popen_with_lines(lines, returncode=0)
        calls: list[tuple[int, int]] = []

        def cb(done: int, total: int, _elapsed: float) -> None:
            calls.append((done, total))

        with patch("subprocess.Popen", return_value=proc):
            rc = runtime.pull_image("podman", "img:tag", progress=cb)

        assert rc == 0
        assert calls == [(0, 1), (0, 2), (1, 2), (2, 2)]

    def test_returns_nonzero_when_pull_fails(self) -> None:
        proc = _popen_with_lines(["Error: pull failed"], returncode=1)
        with patch("subprocess.Popen", return_value=proc):
            rc = runtime.pull_image("docker", "img", progress=None)
        assert rc == 1

    def test_progress_optional(self) -> None:
        proc = _popen_with_lines(["abc: Pulling fs layer"], returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            assert runtime.pull_image("docker", "img") == 0

    def test_no_timeout_kwarg_on_popen(self) -> None:
        proc = _popen_with_lines([], returncode=0)
        with patch("subprocess.Popen", return_value=proc) as popen:
            runtime.pull_image("docker", "img")
        assert "timeout" not in popen.call_args.kwargs


class TestRunContainer:
    def test_includes_gpu_flag_for_docker(self) -> None:
        completed = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            runtime.run_container("docker", "img", gpu=True)
        assert "--gpus" in run.call_args.args[0]

    def test_includes_device_flag_for_podman(self) -> None:
        completed = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            runtime.run_container("podman", "img", gpu=True)
        cmd = run.call_args.args[0]
        assert "--device" in cmd
        assert "nvidia.com/gpu=all" in cmd

    def test_extra_args_go_after_image_name(self) -> None:
        # Regression: extra_args are CMD args for the container, not docker
        # flags. They MUST come after the image name; otherwise docker rejects
        # them with "unknown flag".
        completed = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            runtime.run_container(
                "docker",
                "vllm/vllm-openai:latest",
                extra_args=["--model", "Qwen/Qwen3-0.6B"],
            )
        cmd = run.call_args.args[0]
        image_idx = cmd.index("vllm/vllm-openai:latest")
        model_idx = cmd.index("--model")
        assert image_idx < model_idx

    def test_labels_injected_as_label_flags(self) -> None:
        completed = MagicMock(returncode=0, stdout="cid\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            runtime.run_container(
                "docker",
                "img",
                labels={"relaylm.managed": "true", "relaylm.config": "abc123"},
            )
        cmd = run.call_args.args[0]
        # Labels precede the image name.
        image_idx = cmd.index("img")
        managed_idx = cmd.index("relaylm.managed=true")
        config_idx = cmd.index("relaylm.config=abc123")
        assert managed_idx < image_idx
        assert config_idx < image_idx
        assert cmd[managed_idx - 1] == "--label"
        assert cmd[config_idx - 1] == "--label"


class TestListManagedContainers:
    def test_parses_pipe_separated_rows(self) -> None:
        stdout = "abc123|running|sigA\ndef456|exited|sigB\n"
        completed = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            rows = runtime.list_managed_containers("docker")
        assert rows == [
            ("abc123", "running", "sigA"),
            ("def456", "exited", "sigB"),
        ]
        cmd = run.call_args.args[0]
        assert cmd[:3] == ["docker", "ps", "-a"]
        assert "--filter" in cmd
        idx = cmd.index("--filter")
        assert cmd[idx + 1] == "label=relaylm.managed=true"

    def test_skips_malformed_rows(self) -> None:
        stdout = "abc|running|sigA\n\n|||\ndef|exited|sigB\n"
        completed = MagicMock(returncode=0, stdout=stdout, stderr="")
        with patch("subprocess.run", return_value=completed):
            rows = runtime.list_managed_containers("docker")
        # Empty first column is skipped; otherwise both kept.
        assert rows == [("abc", "running", "sigA"), ("def", "exited", "sigB")]

    def test_returns_empty_on_nonzero_exit(self) -> None:
        completed = MagicMock(returncode=1, stdout="", stderr="boom")
        with patch("subprocess.run", return_value=completed):
            assert runtime.list_managed_containers("docker") == []

    def test_returns_empty_on_subprocess_error(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert runtime.list_managed_containers("docker") == []
        err = subprocess.TimeoutExpired(cmd="docker", timeout=5)
        with patch("subprocess.run", side_effect=err):
            assert runtime.list_managed_containers("docker") == []


class TestContainerStatus:
    def test_returns_stripped_stdout_on_success(self) -> None:
        completed = MagicMock(returncode=0, stdout="running\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            assert runtime.container_status("docker", "cid") == "running"
        cmd = run.call_args.args[0]
        assert cmd == [
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}}",
            "cid",
        ]

    def test_returns_unknown_on_empty_stdout(self) -> None:
        completed = MagicMock(returncode=0, stdout="\n", stderr="")
        with patch("subprocess.run", return_value=completed):
            assert runtime.container_status("docker", "cid") == "unknown"

    def test_returns_unknown_on_nonzero_exit(self) -> None:
        completed = MagicMock(returncode=1, stdout="", stderr="no such container")
        with patch("subprocess.run", return_value=completed):
            assert runtime.container_status("docker", "cid") == "unknown"

    def test_returns_unknown_when_binary_missing(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert runtime.container_status("docker", "cid") == "unknown"

    def test_returns_unknown_on_timeout(self) -> None:
        err = subprocess.TimeoutExpired(cmd="docker", timeout=5)
        with patch("subprocess.run", side_effect=err):
            assert runtime.container_status("docker", "cid") == "unknown"


class TestTailLogs:
    def test_returns_last_non_empty_line(self) -> None:
        completed = MagicMock(
            returncode=0,
            stdout="Loading model weights...\nApplication startup complete\n\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=completed):
            assert runtime.tail_logs("docker", "cid") == "Application startup complete"

    def test_builds_expected_command(self) -> None:
        completed = MagicMock(returncode=0, stdout="x\n", stderr="")
        with patch("subprocess.run", return_value=completed) as run:
            runtime.tail_logs("docker", "cid", lines=5)
        assert run.call_args.args[0] == ["docker", "logs", "--tail", "5", "cid"]

    def test_returns_empty_when_stdout_empty(self) -> None:
        completed = MagicMock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=completed):
            assert runtime.tail_logs("docker", "cid") == ""

    def test_returns_empty_on_nonzero_exit(self) -> None:
        completed = MagicMock(returncode=1, stdout="anything", stderr="")
        with patch("subprocess.run", return_value=completed):
            assert runtime.tail_logs("docker", "cid") == ""

    def test_returns_empty_on_subprocess_error(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert runtime.tail_logs("docker", "cid") == ""
        err = subprocess.TimeoutExpired(cmd="docker", timeout=5)
        with patch("subprocess.run", side_effect=err):
            assert runtime.tail_logs("docker", "cid") == ""


@pytest.fixture(autouse=True)
def _no_real_subprocess() -> None:
    # Defensive: ensure we never accidentally spawn real subprocesses in these tests.
    return None
