# backend/system_monitor.py
import psutil
import GPUtil

class SystemMonitor:
    """On-demand diagnostics tool for CPU, RAM, Disk, and GPU."""

    @staticmethod
    def get_full_overview() -> str:
        cpu_pct = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024**3), 1)
        ram_total_gb = round(ram.total / (1024**3), 1)

        disk = psutil.disk_usage("C:\\")
        disk_free_gb = round(disk.free / (1024**3), 1)
        disk_total_gb = round(disk.total / (1024**3), 1)

        return (
            f"CPU is running at {cpu_pct}%. "
            f"RAM usage is {ram.percent}%, using {ram_used_gb} GB out of {ram_total_gb} GB. "
            f"C drive has {disk_free_gb} GB free out of {disk_total_gb} GB."
        )

    @staticmethod
    def get_gpu_status() -> str:
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return "No dedicated NVIDIA GPU was detected on this system."

            gpu = gpus[0]
            vram_used = round(gpu.memoryUsed / 1024, 1)
            vram_total = round(gpu.memoryTotal / 1024, 1)
            gpu_load = round(gpu.load * 100, 1)
            gpu_temp = f"{gpu.temperature}°C" if gpu.temperature else "N/A"

            return (
                f"GPU ({gpu.name}) is at {gpu_load}% load and {gpu_temp}. "
                f"VRAM usage is {vram_used} GB out of {vram_total} GB."
            )
        except Exception as e:
            return f"Unable to retrieve GPU metrics: {e}"

    @staticmethod
    def get_disk_status() -> str:
        disk = psutil.disk_usage("C:\\")
        free_gb = round(disk.free / (1024**3), 1)
        total_gb = round(disk.total / (1024**3), 1)
        return f"Storage is at {disk.percent}% capacity, with {free_gb} GB free out of {total_gb} GB."