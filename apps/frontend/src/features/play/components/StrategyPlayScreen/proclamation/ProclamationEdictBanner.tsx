import type { ProclamationEdictBannerProps } from "./ProclamationEdictBanner.types";

const formatLabel = (value: string): string => value.replace(/_/g, " ");

export function ProclamationEdictBanner({
  legalSummary,
  domain,
  burden,
}: ProclamationEdictBannerProps) {
  return (
    <section className="relative w-full overflow-hidden rounded-xl bg-parchment-panel/90 p-6 shadow-[0_4px_24px_-4px_rgba(58,49,40,0.08),0_2px_8px_-1px_rgba(58,49,40,0.04)] backdrop-blur-md">
      <div className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-secondary-container/30 blur-2xl" />
      <div className="flex flex-col items-start justify-between gap-4 lg:flex-row lg:items-center">
        <div className="flex items-start gap-4">
          <div className="mt-0.5 flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-surface-container text-secondary shadow-sm">
            <span className="material-symbols-outlined text-[28px]" aria-hidden="true">
              history_edu
            </span>
          </div>
          <div>
            <span className="mb-1 block text-[11px] font-bold uppercase tracking-[0.14em] text-secondary">
              Draft Edict Before the Crown
            </span>
            <h1 className="font-serif text-[32px] italic leading-tight text-on-surface lg:text-[40px]">
              {`“${legalSummary}”`}
            </h1>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 self-end lg:self-center">
          {domain ? (
            <span className="flex items-center gap-1.5 rounded-lg bg-primary-container-wilds px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white shadow-sm">
              <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                shield
              </span>
              {formatLabel(domain)}
            </span>
          ) : null}
          {burden ? (
            <span className="flex items-center gap-1.5 rounded-lg bg-secondary-container px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-on-secondary-container shadow-sm">
              <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                warning
              </span>
              {`${formatLabel(burden)} Burden`}
            </span>
          ) : null}
        </div>
      </div>
    </section>
  );
}
