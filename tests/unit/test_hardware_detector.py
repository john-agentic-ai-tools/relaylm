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
