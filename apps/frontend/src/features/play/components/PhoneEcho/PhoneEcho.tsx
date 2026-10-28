import { usePhoneEcho } from "../../hooks/usePhoneEcho";

export function PhoneEcho() {
  const phase = usePhoneEcho();
  if (phase === "idle") return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="flex flex-col items-center gap-3 font-mono text-sm text-content">
        <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
        <p>Line 14 — open</p>
        {phase === "listening" && <p>Say something.</p>}
      </div>
    </div>
  );
}
