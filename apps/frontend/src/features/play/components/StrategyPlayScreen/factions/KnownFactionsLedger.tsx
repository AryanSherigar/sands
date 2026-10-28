import React from "react";
import { KnownFactionRow } from "./KnownFactionRow";
import type { KnownFactionsLedgerProps } from "./KnownFactionsLedger.types";
import type { PactView } from "../../../types/scene.types";

const WAR_RELATION = "war";

function findPact(pacts: PactView[], factionId: string): PactView | undefined {
  return pacts.find((pact) => pact.faction_a === factionId || pact.faction_b === factionId);
}

export const KnownFactionsLedger: React.FC<KnownFactionsLedgerProps> = ({
  rivals,
  diplomacy,
}) => {
  return (
    <div className="flex flex-col gap-2 p-3">
      <span className="text-[10px] text-[#46606E] font-bold uppercase tracking-wider">
        Known Factions
      </span>
      {rivals.map((rival) => {
        const pact = findPact(diplomacy?.pacts ?? [], rival.faction_id);
        return (
          <KnownFactionRow
            key={rival.faction_id}
            rival={rival}
            pactEndTurn={pact?.end_turn ?? null}
            canProposeTerms={
              Boolean(diplomacy?.isProposalAvailable) &&
              !pact &&
              rival.relation !== WAR_RELATION
            }
            onProposeTerms={diplomacy?.onProposeTerms}
          />
        );
      })}
    </div>
  );
};
