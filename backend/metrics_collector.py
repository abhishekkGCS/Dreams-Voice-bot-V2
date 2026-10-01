import time
import threading
from collections import deque
import statistics

class MetricsCollector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetricsCollector, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.max_events = 200
        self.events = deque(maxlen=self.max_events)
        self.stats = {
            "total_turns": 0,
            "tool_counts": {},
            "fast_path_count": 0,
            "llm_path_count": 0
        }
        self.latencies = {
            "stt": [],
            "llm": [],
            "tts": [],
            "tools": {}
        }
        self.latest_tick = {}
        self.lock = threading.Lock()

    def _add_event(self, event_type, data):
        with self.lock:
            event = {
                "timestamp": time.time(),
                "type": event_type,
                "data": data
            }
            self.events.append(event)
            # update latest tick for broadcast
            if "latest_events" not in self.latest_tick:
                self.latest_tick["latest_events"] = []
            self.latest_tick["latest_events"].append(event)

    def record_stt(self, duration):
        self._add_event("stt", {"duration": duration})
        with self.lock:
            self.latencies["stt"].append(duration)
            if len(self.latencies["stt"]) > 1000:
                self.latencies["stt"].pop(0)

    def record_llm(self, ttft):
        self._add_event("llm", {"ttft": ttft})
        with self.lock:
            self.latencies["llm"].append(ttft)
            if len(self.latencies["llm"]) > 1000:
                self.latencies["llm"].pop(0)

    def record_tts(self, ttfb):
        self._add_event("tts", {"ttfb": ttfb})
        with self.lock:
            self.latencies["tts"].append(ttfb)
            if len(self.latencies["tts"]) > 1000:
                self.latencies["tts"].pop(0)

    def record_tool(self, tool_name, duration_ms, success):
        self._add_event("tool", {"tool_name": tool_name, "duration_ms": duration_ms, "success": success})
        with self.lock:
            if tool_name not in self.stats["tool_counts"]:
                self.stats["tool_counts"][tool_name] = {"success": 0, "fail": 0}
            if success:
                self.stats["tool_counts"][tool_name]["success"] += 1
            else:
                self.stats["tool_counts"][tool_name]["fail"] += 1

            if tool_name not in self.latencies["tools"]:
                self.latencies["tools"][tool_name] = []
            self.latencies["tools"][tool_name].append(duration_ms)
            if len(self.latencies["tools"][tool_name]) > 100:
                self.latencies["tools"][tool_name].pop(0)

    def record_system(self, cpu, ram_pct, ram_used, ram_total, disk_free, disk_total, gpu_load, gpu_vram_used, gpu_vram_total, gpu_temp):
        data = {
            "cpu": cpu,
            "ram_pct": ram_pct,
            "ram_used": ram_used,
            "ram_total": ram_total,
            "disk_free": disk_free,
            "disk_total": disk_total,
            "gpu_load": gpu_load,
            "gpu_vram_used": gpu_vram_used,
            "gpu_vram_total": gpu_vram_total,
            "gpu_temp": gpu_temp
        }
        self._add_event("system", data)
        with self.lock:
            self.latest_tick["system"] = data

    def record_conversation(self, role, text, tool_name=None):
        self._add_event("conversation", {"role": role, "text": text, "tool_name": tool_name})
        with self.lock:
            if role == "user":
                self.stats["total_turns"] += 1
                if not tool_name:
                    self.stats["llm_path_count"] += 1

    def record_health(self, service_name, status):
        self._add_event("health", {"service_name": service_name, "status": status})

    def record_fast_path(self, action):
        self._add_event("fast_path", {"action": action})
        with self.lock:
            self.stats["fast_path_count"] += 1

    def _calc_percentiles(self, data_list):
        if not data_list:
            return {"p50": 0, "p95": 0, "p99": 0}
        s = sorted(data_list)
        return {
            "p50": statistics.median(s),
            "p95": s[int(len(s)*0.95)] if len(s) > 20 else s[-1],
            "p99": s[int(len(s)*0.99)] if len(s) > 100 else s[-1]
        }

    def get_snapshot(self):
        with self.lock:
            latencies_calc = {
                "stt": self._calc_percentiles(self.latencies["stt"]),
                "llm": self._calc_percentiles(self.latencies["llm"]),
                "tts": self._calc_percentiles(self.latencies["tts"]),
                "tools": {k: self._calc_percentiles(v) for k, v in self.latencies["tools"].items()}
            }
            return {
                "events": list(self.events),
                "stats": self.stats,
                "latencies": latencies_calc,
                "system": self.latest_tick.get("system", {})
            }

    def get_broadcast_payload(self):
        with self.lock:
            payload = self.latest_tick.copy()
            self.latest_tick["latest_events"] = []
            
            payload["stats"] = self.stats
            payload["latencies"] = {
                "stt": self._calc_percentiles(self.latencies["stt"]),
                "llm": self._calc_percentiles(self.latencies["llm"]),
                "tts": self._calc_percentiles(self.latencies["tts"]),
            }
            return payload
