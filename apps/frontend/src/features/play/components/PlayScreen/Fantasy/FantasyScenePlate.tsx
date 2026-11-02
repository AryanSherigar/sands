import type { FantasyScenePlateProps } from "./FantasyScenePlate.types";

export function FantasyScenePlate({
  url,
  plateLabel,
  yearLabel,
}: FantasyScenePlateProps) {
  return (
    <section aria-label="Scene illustration plate" className="mb-8 relative rounded-xl overflow-hidden border border-[#382E25] bg-[#0E0E10] shadow-xl">
      <div className="relative w-full aspect-[16/9] overflow-hidden">
        <img
          alt="Scene illustration plate"
          src={url}
          className="w-full h-full object-cover object-center filter brightness-95 contrast-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#111113] via-transparent to-black/30 pointer-events-none" />
        {(plateLabel || yearLabel) && <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between font-mono text-[#8C7A6B]">
          <span className="text-[10px] tracking-wider uppercase font-medium">{plateLabel}</span>
          <span className="text-[10px] font-medium">{yearLabel}</span>
        </div>}
      </div>
    </section>
  );
}
