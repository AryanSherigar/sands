import type { FC } from "react";
import type { ProclamationMinisterView } from "../../../api/proclamation.api";
import {
  PROCLAMATION_ESTATE_STYLES,
  PROCLAMATION_STANCE_STYLES,
} from "../../../constants/proclamation.constants";

export interface ProclamationCouncilTableProps {
  ministers: ProclamationMinisterView[];
}

const FALLBACK_ESTATE_STYLE = "bg-surface-container-high text-on-surface-variant";

export const ProclamationCouncilTable: FC<ProclamationCouncilTableProps> = ({ ministers }) => (
  <section aria-label="The council" className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
    {ministers.map((minister) => {
      const stance =
        PROCLAMATION_STANCE_STYLES[minister.stance] ?? PROCLAMATION_STANCE_STYLES.cautious;
      const estateStyle =
        PROCLAMATION_ESTATE_STYLES[minister.estate.toLowerCase()] ?? FALLBACK_ESTATE_STYLE;
      return (
        <article
          key={minister.title}
          className="flex flex-col justify-between rounded-xl bg-parchment-panel/85 p-4 shadow-[0_4px_20px_-2px_rgba(58,49,40,0.06)] backdrop-blur-md transition-transform duration-200 hover:-translate-y-0.5"
        >
          <div>
            <div className="mb-2 flex items-center justify-between gap-1">
              <span
                className={`rounded px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wider ${estateStyle}`}
              >
                {minister.estate}
              </span>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${stance.className}`}
              >
                <span className="material-symbols-outlined text-[13px]" aria-hidden="true">
                  {stance.icon}
                </span>
                {stance.label}
              </span>
            </div>
            <h2 className="font-serif text-[20px] font-semibold leading-snug text-on-surface">
              {minister.title}
            </h2>
          </div>
          <p className="mt-3 rounded-lg bg-surface-container-low/70 p-2.5 text-[12px] italic leading-relaxed text-on-surface-variant">
            {`“${minister.primary_grievance}”`}
          </p>
        </article>
      );
    })}
  </section>
);
