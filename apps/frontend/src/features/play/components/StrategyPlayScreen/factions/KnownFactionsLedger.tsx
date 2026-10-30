import React from "react";
import { KnownFactionRow } from "./KnownFactionRow";
import type { KnownFactionsLedgerProps } from "./KnownFactionsLedger.types";
import type { PactView } from "../../../types/scene.types";
import type { CallView, PendingDemandView, RivalView, StrategyOrder } from "../../../types/simulation.types";
import {
  buildAnswerCallOrder,
  buildAnswerDemandOrder,
} from "../../../lib/orderBuilders";

const WAR_RELATIONS = ["war", "at_war"];

function findPact(pacts: PactView[], factionId: string): PactView | undefined {
  return pacts.find((pact) => pact.faction_a === factionId || pact.faction_b === factionId);
}

interface PendingObligationsProps {
  calls?: CallView[];
  demands?: PendingDemandView[];
  rivals: RivalView[];
  myFactionId: string;
  onSubmitOrder?: (order: StrategyOrder) => void;
}

export const PendingObligationsSection: React.FC<PendingObligationsProps> = ({
  calls = [],
  demands = [],
  rivals,
  myFactionId,
  onSubmitOrder,
}) => {
  if (calls.length === 0 && demands.length === 0) {
    return null;
  }

  const getFactionName = (factionId: string): string => {
    const match = rivals.find((r) => r.faction_id === factionId);
    return match?.name ?? factionId;
  };

  return (
    <div className="flex flex-col gap-2 pb-2 mb-2 border-b border-[#3A3128]/10">
      <span className="text-[10px] text-[#A8483E] font-bold uppercase tracking-wider">
        Pending Obligations
      </span>
      {calls.map((call) => {
        const callerName = getFactionName(call.caller_id);
        const callType = call.is_defensive ? "Defensive" : "Offensive";
        return (
          <div
            key={call.id}
            className="p-2 rounded-lg bg-[#FAF0E6] border border-[#A8483E]/30 flex flex-col gap-1.5"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#221A12]">
                War Call from {callerName}
              </span>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#A8483E]/15 text-[#A8483E]">
                {callType}
              </span>
            </div>
            <span className="text-[10px] text-[#72787C]">
              Side: {call.side} • Deadline Turn {call.deadline_turn}
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <button
                type="button"
                onClick={() =>
                  onSubmitOrder?.(buildAnswerCallOrder(myFactionId, call.id, true))
                }
                className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#46606E] text-white hover:bg-[#3A5260] transition-colors"
              >
                Honour Call
              </button>
              <button
                type="button"
                onClick={() =>
                  onSubmitOrder?.(buildAnswerCallOrder(myFactionId, call.id, false))
                }
                className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#72787C]/20 text-[#221A12] hover:bg-[#72787C]/30 transition-colors"
              >
                Refuse
              </button>
            </div>
          </div>
        );
      })}
      {demands.map((demand) => {
        const overlordName = getFactionName(demand.overlord_id);
        return (
          <div
            key={demand.id}
            className="p-2 rounded-lg bg-[#FAF0E6] border border-[#A8483E]/30 flex flex-col gap-1.5"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#221A12]">
                Demand from {overlordName}
              </span>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#785A00]/15 text-[#785A00] capitalize">
                {demand.kind}
              </span>
            </div>
            <span className="text-[10px] text-[#72787C]">
              Demanding: {demand.amount} {demand.kind} • Deadline Turn {demand.deadline_turn}
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <button
                type="button"
                onClick={() =>
                  onSubmitOrder?.(buildAnswerDemandOrder(myFactionId, demand.id, "accept"))
                }
                className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#46606E] text-white hover:bg-[#3A5260] transition-colors"
              >
                Comply
              </button>
              <button
                type="button"
                onClick={() =>
                  onSubmitOrder?.(buildAnswerDemandOrder(myFactionId, demand.id, "refuse"))
                }
                className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#72787C]/20 text-[#221A12] hover:bg-[#72787C]/30 transition-colors"
              >
                Refuse
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const KnownFactionsLedger: React.FC<KnownFactionsLedgerProps> = ({
  rivals,
  diplomacy,
  world,
  onSubmitOrder,
}) => {
  const effectiveRivals = rivals.length > 0 ? rivals : (world?.rivals ?? []);
  const myFactionId = world?.my_faction?.id ?? "";

  return (
    <div className="flex flex-col gap-2 p-3">
      <PendingObligationsSection
        calls={world?.pending_calls}
        demands={world?.pending_demands}
        rivals={effectiveRivals}
        myFactionId={myFactionId}
        onSubmitOrder={onSubmitOrder}
      />
      <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-wider">
        Known Factions
      </span>
      {effectiveRivals.map((rival) => {
        const pact = findPact(diplomacy?.pacts ?? [], rival.faction_id);
        const isAtWar = WAR_RELATIONS.includes(rival.relation);
        return (
          <KnownFactionRow
            key={rival.faction_id}
            rival={rival}
            pactEndTurn={pact?.end_turn ?? null}
            canProposeTerms={
              Boolean(diplomacy?.isProposalAvailable) &&
              !pact &&
              !isAtWar
            }
            onProposeTerms={diplomacy?.onProposeTerms}
            onSubmitOrder={onSubmitOrder}
            myFactionId={myFactionId}
          />
        );
      })}
    </div>
  );
};
