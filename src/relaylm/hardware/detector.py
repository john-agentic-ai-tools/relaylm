import os
import shutil
import subprocess
from pathlib import Path

_WSL_NVIDIA_SMI = "/usr/lib/wsl/lib/nvidia-smi"


def _nvidia_smi_path() -> str | None:
    """Locate nvidia-smi, preferring PATH and falling back to the WSL2 location.

    WSL2 with the Windows-side NVIDIA CUDA driver exposes nvidia-smi at
    /usr/lib/wsl/lib/nvidia-smi, but distros don't always add it to PATH.
    """
    found = shutil.which("nvidia-smi")
    if found:
        return found
    if Path(_WSL_NVIDIA_SMI).exists():
        return _WSL_NVIDIA_SMI
    return None


class HardwareProfile:
    def __init__(
        self,
        ram_gb: float,
        cpu_cores: int,
        has_nvidia_gpu: bool = False,
        gpu_vram_gb: list[float] | None = None,
        gpu_vram_free_gb: list[float] | None = None,
        has_amd_gpu: bool = False,
    ):
        self.ram_gb = ram_gb
        self.cpu_cores = cpu_cores
        self.has_nvidia_gpu = has_nvidia_gpu
        self.gpu_vram_gb = gpu_vram_gb or []
        # If free wasn't reported, fall back to total (best-effort).
        self.gpu_vram_free_gb = (
            gpu_vram_free_gb if gpu_vram_free_gb is not None else list(self.gpu_vram_gb)
        )
        self.has_amd_gpu = has_amd_gpu

    @property
    def total_gpu_vram_gb(self) -> float:
        return sum(self.gpu_vram_gb)

    @property
    def max_gpu_vram_gb(self) -> float:
        return max(self.gpu_vram_gb) if self.gpu_vram_gb else 0.0

    @property
    def max_gpu_vram_free_gb(self) -> float:
        return max(self.gpu_vram_free_gb) if self.gpu_vram_free_gb else 0.0

    def __repr__(self) -> str:
        return (
            f"HardwareProfile(ram={self.ram_gb}GB, cpu={self.cpu_cores} cores, "
            f"nvidia={self.has_nvidia_gpu}, "
            f"vram_total={self.gpu_vram_gb}, vram_free={self.gpu_vram_free_gb}, "
            f"amd={self.has_amd_gpu})"
        )


def _read_meminfo() -> float:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / 1024 / 1024, 1)
    except FileNotFoundError:
        pass
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return round(int(result.stdout.strip()) / 1024**3, 1)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 16.0


def _read_cpu_cores() -> int:
    try:
        return os.cpu_count() or 4
    except NotImplementedError:
        return 4


def _detect_nvidia_gpu() -> tuple[bool, list[float], list[float]]:
    """Return (present, vram_total_gb, vram_free_gb) per GPU."""
    binary = _nvidia_smi_path()
    if binary is None:
        return (False, [], [])
    try:
        result = subprocess.run(
            [
                binary,
                "--query-gpu=memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            totals: list[float] = []
            frees: list[float] = []
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2 or not parts[0]:
                    continue
                totals.append(round(int(parts[0]) / 1024, 1))
                frees.append(round(int(parts[1]) / 1024, 1))
            return (len(totals) > 0, totals, frees)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return (False, [], [])


def _detect_amd_gpu() -> bool:
    try:
        result = subprocess.run(
            ["rocm-smi"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def detect() -> HardwareProfile:
    ram_gb = _read_meminfo()
    cpu_cores = _read_cpu_cores()
    has_nvidia, vram_total, vram_free = _detect_nvidia_gpu()
    has_amd = _detect_amd_gpu() if not has_nvidia else False
    return HardwareProfile(
        ram_gb=ram_gb,
        cpu_cores=cpu_cores,
        has_nvidia_gpu=has_nvidia,
        gpu_vram_gb=vram_total,
        gpu_vram_free_gb=vram_free,
        has_amd_gpu=has_amd,
    )
