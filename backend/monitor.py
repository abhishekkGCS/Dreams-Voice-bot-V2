# import psutil
# import time
# import asyncio
# import GPUtil
# import logging

# logger = logging.getLogger("system_monitor")
# logger.setLevel(logging.INFO)

# # Create a stream handler to output to console
# if not logger.handlers:
#     ch = logging.StreamHandler()
#     ch.setLevel(logging.INFO)
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)


# def get_ollama_process():
#     """Find the Ollama process if it's running."""
#     for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
#         try:
#             name = proc.info['name'].lower()
#             cmdline = proc.info['cmdline']
            
#             # Look for the 'ollama' executable
#             if 'ollama' in name or (cmdline and any('ollama' in cmd.lower() for cmd in cmdline)):
#                 return proc
#         except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
#             pass
#     return None


# async def log_system_metrics(interval_seconds=5.0):
#     """
#     Periodically checks the CPU, RAM, and GPU usage.
#     Specific focus on the Ollama process.
#     """
#     logger.info(f"Starting system monitor. Polling every {interval_seconds} seconds.")
    
#     ollama_proc = get_ollama_process()
#     if ollama_proc:
#         logger.info(f"Found Ollama process (PID: {ollama_proc.pid})")
#     else:
#         logger.warning("Ollama process not found. System stats will still be logged.")

#     while True:
#         try:
#             metrics = {}
            
#             # --- System CPU & RAM ---
#             metrics['sys_cpu_percent'] = psutil.cpu_percent(interval=None)
#             mem = psutil.virtual_memory()
#             metrics['sys_ram_percent'] = mem.percent
#             metrics['sys_ram_used_gb'] = round(mem.used / (1024**3), 2)
            
#             # --- Ollama CPU & RAM ---
#             if ollama_proc and ollama_proc.is_running():
#                 # Note: cpu_percent() for a process can be > 100% on multi-core
#                 metrics['ollama_cpu_percent'] = ollama_proc.cpu_percent(interval=None)
#                 metrics['ollama_ram_mb'] = round(ollama_proc.memory_info().rss / (1024**2), 2)
#             else:
#                 # Try to find it again if it restarted
#                 ollama_proc = get_ollama_process()
            
#             # --- GPU Stats (via GPUtil) ---
#             gpus = GPUtil.getGPUs()
#             if gpus:
#                 # We assume the first GPU for now
#                 gpu = gpus[0]
#                 metrics['gpu_load'] = round(gpu.load * 100, 2)
#                 metrics['gpu_memory_used_mb'] = gpu.memoryUsed
#                 metrics['gpu_memory_total_mb'] = gpu.memoryTotal
#                 metrics['gpu_temp_c'] = gpu.temperature
            
#             logger.info("System Metrics", extra=metrics)
            
#             # Also print a human-readable summary
#             summary = f"SYS CPU: {metrics['sys_cpu_percent']}% | RAM: {metrics['sys_ram_percent']}%"
#             if 'ollama_cpu_percent' in metrics:
#                 summary += f" | OLLAMA CPU: {metrics['ollama_cpu_percent']}% RAM: {metrics['ollama_ram_mb']}MB"
#             if 'gpu_load' in metrics:
#                 summary += f" | GPU Load: {metrics['gpu_load']}% VRAM: {metrics['gpu_memory_used_mb']}MB/{metrics['gpu_memory_total_mb']}MB Temp: {metrics['gpu_temp_c']}C"
            
#             logger.info(summary)

#         except Exception as e:
#             logger.error(f"Error gathering system metrics: {e}")
            
#         await asyncio.sleep(interval_seconds)

# if __name__ == "__main__":
#     # For testing standalone
#     asyncio.run(log_system_metrics(2.0))



import psutil
import time
import asyncio
import GPUtil

async def monitor_ollama(interval = 1.0):
    # Background task to monitor CPU, RAM and GPU usage of the Ollama process
    
    # Find the ollama process
    # we iterate through all the running processes on the computer
    # We look for the process named ollama
    ollama_process = None
    
    for proc in psutil.process_iter(['pid', 'name']):
        if "ollama" in proc.info["name"].lower():
            ollama_process = psutil.Process(proc.info["pid"])
            break
    
    if not ollama_process:
        print("Ollama process not found. Please ensure Ollama is running.")
        return
    
    # the monitoring loop
    # we use an infinite while loop that runs continuously in the background
    while True:
        try:
            # Calculate CPU & RAM
            cpu_percent = ollama_process.cpu_percent(interval=None)
            ram_mb = ollama_process.memory_info().rss / (1024 * 1024)  # Convert to MB

            # Calculate GPU (if present)
            gpu_stats = ""
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_stats = f"| GPU: {gpu.load * 100:.1f}% | VRAM: {gpu.memoryUsed}MB/{gpu.memoryTotal}MB"
                
            # Output the metrics
            print(f"[Ollama Monitor] CPU: {cpu_percent:.1f}% | RAM: {ram_mb:.2f} MB {gpu_stats}")
            
        except psutil.NoSuchProcess:
            # If Ollama crashes or closes, the monitor catches the error and stops gracefully.
            print("Ollama process ended.")
            break
            
        # Wait for the specified interval before checking again
        await asyncio.sleep(interval)