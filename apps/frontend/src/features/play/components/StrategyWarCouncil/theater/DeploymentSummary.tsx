import { formatTroopLabel } from "../../../lib/battleReports";

export interface DeploymentSummaryProps {
  active?: Record<string, number>;
  reserve?: Record<string, number>;
}

function DeploymentRow({ title, counts }: { title: string; counts: Record<string, number> }) {
  const entries = Object.entries(counts).filter(([, count]) => count > 0);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-bold uppercase tracking-wider text-[#72787C]">{title}</span>
      {entries.length === 0 ? (
        <span className="text-[12px] italic text-[#42474b]">None</span>
      ) : (
        entries.map(([troopType, count]) => (
          <span key={troopType} className="flex justify-between gap-4 text-[12px] text-[#221A12]">
            <span>{formatTroopLabel(troopType)}</span>
            <span className="font-mono font-bold">{count.toLocaleString()}</span>
          </span>
        ))
      )}
    </div>
  );
}

export function DeploymentSummary({ active, reserve }: DeploymentSummaryProps) {
  if (!active && !reserve) return null;
  return (
    <section
      aria-label="Troops in the line and in reserve"
      className="grid w-full grid-cols-2 gap-3 rounded-xl border border-[#3A3128]/15 bg-[#fff8f4]/90 p-3 shadow-sm"
    >
      <DeploymentRow title="In the line" counts={active ?? {}} />
      <DeploymentRow title="Held in reserve" counts={reserve ?? {}} />
    </section>
  );
}
