export function JudgmentPanorama() {
  return (
    <div
      role="img"
      aria-label="The great hall seen from the high dais"
      className="relative h-[200px] w-full overflow-hidden rounded-lg border border-[#3A3128]/10 bg-gradient-to-t from-[#F7F0DC] via-[#DCE7EA] to-[#C7D3D6] shadow-[0_4px_24px_-4px_rgba(58,49,40,0.18)]"
    >
      <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded bg-[#382f26]/75 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-[#feeee0]">
        <span className="material-symbols-outlined text-[14px]" aria-hidden="true">
          visibility
        </span>
        Dais sightline
      </span>
    </div>
  );
}
