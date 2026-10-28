import React from "react";
import type { KnownFactionRowProps } from "./KnownFactionRow.types";

export const KnownFactionRow: React.FC<KnownFactionRowProps> = ({
  rival,
  pactEndTurn = null,
  canProposeTerms = false,
  onProposeTerms,
}) => {
  const relationText = rival.relation.replace(/_/g, " ");
  const relationClass = rival.relation === "war" ? "text-[#A8483E]" : "text-[#5E8A5A]";

  return (
    <div className="p-2 rounded-lg bg-[#F5E5D8]/70 border border-[#3A3128]/10 flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <div className="flex flex-col leading-tight">
          <span className="text-xs font-bold text-[#221A12]">{rival.name}</span>
          <span className="text-[10px] text-[#72787C]">{rival.leader_name}</span>
        </div>
        <span className={`text-xs font-bold capitalize ${relationClass}`}>
          {relationText}
        </span>
      </div>
      {pactEndTurn !== null ? (
        <span className="text-[10px] text-[#46606E]">
          Non-aggression pact until turn {pactEndTurn}
        </span>
      ) : null}
      {canProposeTerms && onProposeTerms ? (
        <button
          type="button"
          onClick={() => onProposeTerms(rival.faction_id)}
          className="self-start text-[11px] font-bold px-2 py-0.5 rounded bg-[#46606E] text-white hover:bg-[#3A5260] transition-colors"
        >
          Propose terms
        </button>
      ) : null}
    </div>
  );
};
