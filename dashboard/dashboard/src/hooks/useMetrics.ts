// src/hooks/useMetrics.ts
import { useState, useEffect, useRef, useCallback } from "react";

export interface LatencyPercentiles {
  p50: number;
  p95: number;
  p99: number;
}

export interface SystemData {
  cpu?: number;
  ram_pct?: number;
  ram_used?: number;
  ram_total?: number;
  disk_free?: number;
  disk_total?: number;
  gpu_load?: number;
  gpu_vram_used?: number;
  gpu_vram_total?: number;
  gpu_temp?: number;
}

export interface MetricsSnapshot {
  events: Array<{ timestamp: number; type: string; data: any }>;
  stats: {
    total_turns: number;
    tool_counts: Record<string, { success: number; fail: number }>;
    fast_path_count: number;
    llm_path_count: number;
  };
  latencies: {
    stt: LatencyPercentiles;
    llm: LatencyPercentiles;
    tts: LatencyPercentiles;
    tools: Record<string, LatencyPercentiles>;
  };
  system: SystemData;
}

export function useMetrics(url: string = "ws://localhost:8765") {
  const [data, setData] = useState<MetricsSnapshot | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "snapshot") {
            setData(message.data);
          } else if (message.type === "broadcast") {
            setData((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                stats: message.data.stats || prev.stats,
                latencies: { ...prev.latencies, ...message.data.latencies },
                system: message.data.system || prev.system,
                events: [...prev.events, ...(message.data.latest_events || [])].slice(-200),
              };
            });
          }
        } catch {
          /* ignore parse errors */
        }
      };
    } catch {
      setTimeout(connect, 2000);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { data, connected };
}