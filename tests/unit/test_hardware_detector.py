import subprocess
from unittest.mock import MagicMock, patch

from relaylm.hardware import detector
from relaylm.hardware.detector import HardwareProfile, _read_cpu_cores, _read_meminfo


class TestHardwareProfile:
    def test_basic_profile(self) -> None:
        hp = HardwareProfile(ram_gb=16.0, cpu_cores=8)
        assert hp.ram_gb == 16.0
        assert hp.cpu_cores == 8
        assert hp.has_nvidia_gpu is False
        assert hp.gpu_vram_gb == []
        assert hp.has_amd_gpu is False

    def test_gpu_profile(self) -> None:
        hp = HardwareProfile(
            ram_gb=32.0, cpu_cores=16, has_nvidia_gpu=True, gpu_vram_gb=[8.0, 8.0]
        )
        assert hp.has_nvidia_gpu is True
        assert hp.gpu_vram_gb == [8.0, 8.0]
        assert hp.total_gpu_vram_gb == 16.0

    def test_amd_profile(self) -> None:
        hp = HardwareProfile(
            ram_gb=16.0, cpu_cores=8, has_amd_gpu=True, gpu_vram_gb=[16.0]
        )
        assert hp.has_amd_gpu is True
        assert hp.total_gpu_vram_gb == 16.0

    def test_repr(self) -> None:
        hp = HardwareProfile(ram_gb=8.0, cpu_cores=4)
        assert "ram=8.0GB" in repr(hp)
        assert "cpu=4 cores" in repr(hp)


class TestReadMeminfo:
    def test_returns_float(self) -> None:
        result = _read_meminfo()
        assert isinstance(result, float)
        assert result > 0


class TestReadCpuCores:
    def test_returns_positive_int(self) -> None:
        result = _read_cpu_cores()
        assert isinstance(result, int)
        assert result > 0


class TestNvidiaSmiPath:
    def test_returns_path_lookup_when_present(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
            assert detector._nvidia_smi_path() == "/usr/bin/nvidia-smi"

    def test_falls_back_to_wsl_path_when_present(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.exists", return_value=True),
        ):
            assert detector._nvidia_smi_path() == detector._WSL_NVIDIA_SMI

    def test_returns_none_when_both_missing(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.exists", return_value=False),
        ):
            assert detector._nvidia_smi_path() is None


class TestDetectNvidiaGpu:
    def test_returns_false_when_no_binary(self) -> None:
        with patch.object(detector, "_nvidia_smi_path", return_value=None):
            assert detector._detect_nvidia_gpu() == (False, [])

    def test_parses_vram_when_binary_found(self) -> None:
        completed = MagicMock(returncode=0, stdout="8192\n", stderr="")
        with (
            patch.object(
                detector, "_nvidia_smi_path", return_value="/usr/bin/nvidia-smi"
            ),
            patch("subprocess.run", return_value=completed) as run,
        ):
            assert detector._detect_nvidia_gpu() == (True, [8.0])
        cmd = run.call_args.args[0]
        assert cmd[0] == "/usr/bin/nvidia-smi"

    def test_uses_wsl_binary_when_resolved(self) -> None:
        completed = MagicMock(returncode=0, stdout="8192\n", stderr="")
        with (
            patch.object(
                detector, "_nvidia_smi_path", return_value=detector._WSL_NVIDIA_SMI
            ),
            patch("subprocess.run", return_value=completed) as run,
        ):
            detector._detect_nvidia_gpu()
        assert run.call_args.args[0][0] == detector._WSL_NVIDIA_SMI

    def test_returns_false_when_binary_present_but_call_fails(self) -> None:
        with (
            patch.object(
                detector, "_nvidia_smi_path", return_value=detector._WSL_NVIDIA_SMI
            ),
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=10),
            ),
        ):
            assert detector._detect_nvidia_gpu() == (False, [])
