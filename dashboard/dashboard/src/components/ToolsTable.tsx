// src/components/ToolsTable.tsx
interface Props {
  counts: Record<string, { success: number; fail: number }>;
}

export function ToolsTable({ counts }: Props) {
  const entries = Object.entries(counts);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-5">
      <h3 className="mb-4 text-sm font-semibold tracking-wide text-zinc-300">
        Tool Executions & Success Rates
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-xs text-zinc-400">
              <th className="pb-2">Tool Name</th>
              <th className="pb-2">Success</th>
              <th className="pb-2">Fail</th>
              <th className="pb-2">Success Rate</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([name, stat]) => {
              const total = stat.success + stat.fail;
              const rate = total > 0 ? Math.round((stat.success / total) * 100) : 100;
              return (
                <tr key={name} className="border-b border-zinc-800/40">
                  <td className="py-2.5 font-mono text-cyan-400">{name}</td>
                  <td className="py-2.5 text-emerald-400">{stat.success}</td>
                  <td className="py-2.5 text-rose-400">{stat.fail}</td>
                  <td className="py-2.5 font-semibold text-zinc-200">{rate}%</td>
                </tr>
              );
            })}
            {entries.length === 0 && (
              <tr>
                <td colSpan={4} className="py-4 text-center text-zinc-500">
                  No tools called yet in this session.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}