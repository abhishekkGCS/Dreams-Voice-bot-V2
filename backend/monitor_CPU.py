# import psutil
# import time
# import asyncio
# import GPUtil

# async def monitor_ollama(interval1 = 1.0):
#     # Background task to monitor CPU, RAM and GPU usage of the Ollama process
    
#     # Find the ollama process
#     # we iterate throuhg all the runnig proess on the computer
#     # We look for the ptocess named ollama
#     ollama_process = None
    
#     for proc in psutil.process_iter(['pid', 'name']):
#         if "ollama" in proc.info["name"].lower():
#             ollama_process = psutil.Process(proc.info["pid"])
#             break
    
#     if not ollama_process:
#         print("Ollama process not found. Please ensure Ollama is running.")
#         return
    
#     # the monitoring loop
#     # we use an infite while loop that runs continuesly in the background
    
#     while True:
#         # Calculate CPU & RAM
#         # . CPU_percent(interval = None) returns the CPU usage of the process the script
#         # .memory_info() gets the exact bytes of RAM the process is using
#         try:
#             cpu_usage = ollama_process.cpu_percent(interval=None)
#             ram_usage = ollama_process.memory_info().rss / (1024 * 1024)  # Convert to MB
#             ram_mb = ollama_process.memory_info().rss / (1024 * 1024)  # Convert to MB
#         except psutil.NoSuchProcess:
#             print("Ollama process ended.")
#             break

#         # Calculate GPU (if preset)
#         # GPU til fetches stats for Nvidia GPU. we grb the first gpu [0]
        
#         gpu_stats = ""
#         gpus = GPUtil.getGPUs()
#         if gpus:
#             gpu = gpus[0]
#             gpu_stats = f"| GPU: {gpu.load * 100:.1f}% | VRAM: {gpu.memoryUsed}MB/{gpu.memoryTotal}MB"
            
#         # Block 5: Output the metrics
#         print(f"[Ollama Monitor] CPU: {cpu_percent:.1f}% | RAM: {ram_mb:.2f} MB {gpu_stats}")
        
#     # Wait for the specified interval (default 1 second) before checking again
#     await asyncio.sleep(interval)
    
    