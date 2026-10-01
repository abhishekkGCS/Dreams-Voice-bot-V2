// src/components/LatencyChart.tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Props {
  events: Array<{ timestamp: number; type: string; data: any }>;
}

export function LatencyChart({ events }: Props) {
  // Extract and format latency samples for Recharts
  const chartData = events
    .filter((e) => ["stt", "llm", "tts"].includes(e.type))
    .slice(-30)
    .map((e) => ({
      time: new Date(e.timestamp * 1000).toLocaleTimeString(),
      STT: e.type === "stt" ? Math.round(e.data.duration * 1000) : undefined,
      LLM: e.type === "llm" ? Math.round(e.data.ttft * 1000) : undefined,
      TTS: e.type === "tts" ? Math.round(e.data.ttfb * 1000) : undefined,
    }));

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-5">
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-zinc-300">
        Live Latency Timeline (ms)
      </h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="time" stroke="#71717a" fontSize={11} />
            <YAxis stroke="#71717a" fontSize={11} unit="ms" />
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181b",
                border: "1px solid #3f3f46",
                borderRadius: "8px",
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="STT" stroke="#38bdf8" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="LLM" stroke="#a855f7" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="TTS" stroke="#f97316" strokeWidth={2} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}