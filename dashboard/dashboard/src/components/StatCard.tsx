// src/components/StatCard.tsx
interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}

export function StatCard({ title, value, subtitle, color = "text-white" }: StatCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-5 backdrop-blur">
      <p className="text-xs uppercase tracking-wider text-zinc-400">{title}</p>
      <p className={`mt-2 text-3xl font-bold tracking-tight ${color}`}>{value}</p>
      {subtitle && <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>}
    </div>
  );
}