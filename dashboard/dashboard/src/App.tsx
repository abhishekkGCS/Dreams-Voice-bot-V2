// src/App.tsx
import { useMetrics } from "./hooks/useMetrics";
import { StatCard } from "./components/StatCard";
import { LatencyChart } from "./components/LatencyChart";
import { ToolsTable } from "./components/ToolsTable";

export default function App() {
  const { data, connected } = useMetrics("ws://localhost:8765");

  if (!data) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 text-zinc-400">
        <div className="text-center">
          <div className="mb-3 text-4xl">🎙️</div>
          <p className="text-lg font-medium text-white">Connecting to Dreams Voice Agent...</p>
          <p className="mt-1 text-sm text-zinc-500">Listening on ws://localhost:8765</p>
        </div>
      </div>
    );
  }

  const { stats, latencies, system, events } = data;

  return (
    <div className="min-h-screen bg-zinc-950 p-8 text-white">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between border-b border-zinc-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dreams Voice Assistant</h1>
          <p className="text-sm text-zinc-400">Real-Time Observability & Latency Dashboard (Phase 9)</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1">
          <span className={`h-2.5 w-2.5 rounded-full ${connected ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
          <span className="text-xs font-medium text-zinc-300">{connected ? "LIVE AGENT CONNECTED" : "OFFLINE"}</span>
        </div>
      </div>

      {/* Latency Percentiles Row */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          title="STT Latency (p50)"
          value={`${Math.round(latencies.stt.p50 * 1000)}ms`}
          subtitle={`p95: ${Math.round(latencies.stt.p95 * 1000)}ms | p99: ${Math.round(latencies.stt.p99 * 1000)}ms`}
          color="text-sky-400"
        />
        <StatCard
          title="LLM First Token (p50)"
          value={`${Math.round(latencies.llm.p50 * 1000)}ms`}
          subtitle={`p95: ${Math.round(latencies.llm.p95 * 1000)}ms | p99: ${Math.round(latencies.llm.p99 * 1000)}ms`}
          color="text-purple-400"
        />
        <StatCard
          title="TTS First Byte (p50)"
          value={`${Math.round(latencies.tts.p50 * 1000)}ms`}
          subtitle={`p95: ${Math.round(latencies.tts.p95 * 1000)}ms | p99: ${Math.round(latencies.tts.p99 * 1000)}ms`}
          color="text-amber-400"
        />
        <StatCard
          title="Total Spoken Turns"
          value={stats.total_turns}
          subtitle={`Fast Path: ${stats.fast_path_count} | LLM: ${stats.llm_path_count}`}
          color="text-emerald-400"
        />
      </div>

      {/* Hardware Diagnostics Row */}
      {system.cpu !== undefined && (
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard title="CPU Load" value={`${system.cpu}%`} color="text-zinc-200" />
          <StatCard title="RAM Used" value={`${system.ram_used} GB`} subtitle={`${system.ram_pct}% of ${system.ram_total} GB`} color="text-zinc-200" />
          <StatCard title="Disk Free" value={`${system.disk_free} GB`} subtitle={`Total: ${system.disk_total} GB`} color="text-zinc-200" />
          <StatCard title="GPU Load" value={system.gpu_load !== undefined ? `${system.gpu_load}%` : "N/A"} subtitle={system.gpu_temp ? `Temp: ${system.gpu_temp}°C` : undefined} color="text-zinc-200" />
        </div>
      )}

      {/* Chart & Tool Table */}
      <div className="grid gap-6 lg:grid-cols-2">
        <LatencyChart events={events} />
        <ToolsTable counts={stats.tool_counts} />
      </div>
    </div>
  );
}