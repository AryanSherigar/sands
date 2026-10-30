import React from "react";
import type { KnownFactionRowProps } from "./KnownFactionRow.types";
import {
  buildDeclareWarOrder,
  buildSendEnvoyOrder,
  buildSuePeaceOrder,
} from "../../../lib/orderBuilders";

export const KnownFactionRow: React.FC<KnownFactionRowProps> = ({
  rival,
  pactEndTurn = null,
  canProposeTerms = false,
  onProposeTerms,
  onSubmitOrder,
  myFactionId = "",
  onSuePeace,
  onSendEnvoy,
  onDeclareWar,
}) => {
  const isAtWar = rival.relation === "war" || rival.relation === "at_war";
  const relationText = rival.relation.replace(/_/g, " ");
  const relationClass = isAtWar ? "text-[#A8483E]" : "text-[#5E8A5A]";

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
      {isAtWar ? (
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => {
              onSuePeace?.(rival.faction_id);
              if (onSubmitOrder) {
                onSubmitOrder(buildSuePeaceOrder(myFactionId, rival.faction_id));
              }
            }}
            className="self-start text-[11px] font-bold px-2 py-0.5 rounded bg-[#A8483E] text-white hover:bg-[#8F3B32] transition-colors"
          >
            Sue for Peace
          </button>
          {onProposeTerms ? (
            <button
              type="button"
              onClick={() => onProposeTerms(rival.faction_id)}
              className="self-start text-[11px] font-bold px-2 py-0.5 rounded bg-[#46606E] text-white hover:bg-[#3A5260] transition-colors"
            >
              Peace Talks
            </button>
          ) : null}
        </div>
      ) : (
        <div className="flex items-center gap-1.5 flex-wrap">
          {canProposeTerms && onProposeTerms ? (
            <button
              type="button"
              onClick={() => onProposeTerms(rival.faction_id)}
              className="self-start text-[11px] font-bold px-2 py-0.5 rounded bg-[#46606E] text-white hover:bg-[#3A5260] transition-colors"
            >
              Propose terms
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              onSendEnvoy?.(rival.faction_id);
              if (onSubmitOrder) {
                onSubmitOrder(buildSendEnvoyOrder(myFactionId, rival.faction_id));
              }
            }}
            className="self-start text-[11px] font-bold px-2 py-0.5 rounded bg-[#46606E] text-white hover:bg-[#3A5260] transition-colors"
          >
            Send Envoy
          </button>
          <button
            type="button"
            onClick={() => {
              onDeclareWar?.(rival.faction_id);
              if (onSubmitOrder) {
                onSubmitOrder(buildDeclareWarOrder(myFactionId, rival.faction_id));
              }
            }}
            className="self-start text-[11px] font-bold px-2 py-0.5 rounded bg-[#A8483E] text-white hover:bg-[#8F3B32] transition-colors"
          >
            Declare War
          </button>
        </div>
      )}
    </div>
  );
};
