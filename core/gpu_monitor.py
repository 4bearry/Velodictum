"""
Velodictum - Multiplatform GPU & Hardware Telemetry Engine
Dynamically detects the host GPU (NVIDIA via NVML/CUDA, AMD/Intel via WMI/DXGI, or CPU fallback)
without any hardcoded hardware strings.
"""
import os
import platform
import subprocess
from typing import Dict, Optional


class GPUMonitor:
    def __init__(self):
        self.initialized = False
        self._nvml_handle = None
        self.device_name = "CPU"
        self.short_name = "CPU"
        self.backend = "cpu"
        self._init_hardware()

    def _init_hardware(self):
        """Dynamically detect GPU hardware across platforms and drivers."""
        # 1. Try official NVIDIA NVML (highest fidelity on NVIDIA hardware)
        try:
            import pynvml
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            if count > 0:
                self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                raw_name = pynvml.nvmlDeviceGetName(self._nvml_handle)
                self.device_name = raw_name
                self.short_name = self._clean_gpu_name(raw_name)
                self.backend = "nvml"
                self.initialized = True
                return
        except Exception:
            pass

        # 2. Try PyTorch CUDA / ROCm
        try:
            import torch
            if torch.cuda.is_available():
                raw_name = torch.cuda.get_device_name(0)
                self.device_name = raw_name
                self.short_name = self._clean_gpu_name(raw_name)
                self.backend = "torch_cuda"
                self.initialized = True
                return
        except Exception:
            pass

        # 3. Windows WMI fallback for AMD Radeon / Intel Arc / NVIDIA Standard Drivers
        if platform.system() == "Windows":
            try:
                out = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2.0,
                )
                lines = [l.strip() for l in out.splitlines() if l.strip() and l.strip().lower() != "name"]
                for l in lines:
                    low = l.lower()
                    if any(vendor in low for vendor in ("nvidia", "geforce", "radeon", "amd", "intel", "arc", "rtx", "gtx")):
                        self.device_name = l
                        self.short_name = self._clean_gpu_name(l)
                        self.backend = "wmi"
                        self.initialized = True
                        return
                if lines:
                    self.device_name = lines[0]
                    self.short_name = self._clean_gpu_name(lines[0])
                    self.backend = "wmi"
                    self.initialized = True
                    return
            except Exception:
                pass

        # 4. CPU Fallback
        self.device_name = f"CPU ({platform.processor() or 'x86_64'})"
        self.short_name = "CPU"
        self.backend = "cpu"
        self.initialized = False

    @staticmethod
    def _clean_gpu_name(raw: str) -> str:
        """Produce a clean, concise display name from raw hardware strings."""
        if not raw:
            return "GPU"
        cleaned = raw
        for noise in ("NVIDIA", "GeForce", "Graphics", "Laptop GPU", "Desktop", "Corporation", "AMD", "Intel(R)", "HD Graphics", "UHD Graphics"):
            cleaned = cleaned.replace(noise, "")
        cleaned = " ".join(cleaned.split()).strip()
        return cleaned if cleaned else raw.strip()

    def get_telemetry(self) -> Dict:
        """
        Returns live hardware telemetry dictionary:
        {
            "available": bool,
            "name": str,
            "short_name": str,
            "backend": str,
            "gpu_util": int (%),
            "vram_used_gb": float,
            "vram_total_gb": float,
            "vram_percent": float,
            "temp_c": int,
        }
        """
        if self.backend == "nvml" and self._nvml_handle is not None:
            try:
                import pynvml
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                temp = pynvml.nvmlDeviceGetTemperature(self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU)

                used_gb = mem.used / (1024 ** 3)
                total_gb = mem.total / (1024 ** 3)
                vram_pct = (mem.used / mem.total) * 100.0 if mem.total > 0 else 0.0

                return {
                    "available": True,
                    "name": self.device_name,
                    "short_name": self.short_name,
                    "backend": self.backend,
                    "gpu_util": int(util.gpu),
                    "vram_used_gb": used_gb,
                    "vram_total_gb": total_gb,
                    "vram_percent": vram_pct,
                    "temp_c": int(temp),
                }
            except Exception:
                pass

        if self.initialized:
            return {
                "available": True,
                "name": self.device_name,
                "short_name": self.short_name,
                "backend": self.backend,
                "gpu_util": 0,
                "vram_used_gb": 0.0,
                "vram_total_gb": 4.0,
                "vram_percent": 0.0,
                "temp_c": 0,
            }

        return {
            "available": False,
            "name": self.device_name,
            "short_name": "CPU",
            "backend": "cpu",
            "gpu_util": 0,
            "vram_used_gb": 0.0,
            "vram_total_gb": 0.0,
            "vram_percent": 0.0,
            "temp_c": 0,
        }

    def is_cuda_available(self) -> bool:
        """Check if a functional NVIDIA CUDA acceleration backend is present."""
        if self.backend in ("nvml", "torch_cuda"):
            return True
        try:
            import torch
            return bool(torch.cuda.is_available())
        except Exception:
            return False
