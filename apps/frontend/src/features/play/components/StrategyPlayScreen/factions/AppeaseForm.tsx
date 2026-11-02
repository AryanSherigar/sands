import { useState } from "react";
import { buildAppeaseOrder } from "../../../lib/orderBuilders";
import type { FormOption } from "../../../lib/realmAffairs";
import type { AppeaseOffer, StrategyOrder } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface AppeaseFormProps {
  factionId: string;
  members: FormOption[];
  claimedRegionsByMember: Record<string, FormOption[]>;
  onSubmit: (order: StrategyOrder) => void;
  onCancel: () => void;
}

type OfferKind = AppeaseOffer["kind"];

const DEFAULT_GOLD = 50;
const DEFAULT_PACT_TURNS = 6;

function buildOffer(kind: OfferKind, gold: number, pactTurns: number, regionId: string): AppeaseOffer {
  if (kind === "gold") return { kind, amount: gold };
  if (kind === "pact") return { kind, duration_turns: pactTurns };
  return { kind, region_id: regionId };
}

export function AppeaseForm({ factionId, members, claimedRegionsByMember, onSubmit, onCancel }: AppeaseFormProps) {
  const [memberId, setMemberId] = useState(members[0]?.id ?? "");
  const [kind, setKind] = useState<OfferKind>("gold");
  const [gold, setGold] = useState(DEFAULT_GOLD);
  const [pactTurns, setPactTurns] = useState(DEFAULT_PACT_TURNS);
  const claimed = claimedRegionsByMember[memberId] ?? [];
  const [regionId, setRegionId] = useState("");
  const effectiveRegionId = claimed.some((region) => region.id === regionId) ? regionId : (claimed[0]?.id ?? "");
  const isValid = Boolean(memberId) && (kind !== "claim_cession" || Boolean(effectiveRegionId));

  return (
    <StrategyFormDialog
      title="Appease a coalition member"
      description="Make an offer to one member. If it is not enough, nothing is paid and they will not hear another offer for a while."
      submitLabel="Make the offer"
      isSubmitDisabled={!isValid}
      onSubmit={() => onSubmit(buildAppeaseOrder(factionId, memberId, buildOffer(kind, gold, pactTurns, effectiveRegionId)))}
      onCancel={onCancel}
    >
      <FormField label="Member">
        <select className={FORM_INPUT_CLASS} value={memberId} onChange={(event) => setMemberId(event.target.value)}>
          {members.map((member) => (
            <option key={member.id} value={member.id}>{member.label}</option>
          ))}
        </select>
      </FormField>
      <FormField label="Offer">
        <select className={FORM_INPUT_CLASS} value={kind} onChange={(event) => setKind(event.target.value as OfferKind)}>
          <option value="gold">Gold</option>
          <option value="pact">A non-aggression pact</option>
          <option value="claim_cession">Hand over a region they claim</option>
        </select>
      </FormField>
      {kind === "gold" ? (
        <FormField label="Gold">
          <input className={FORM_INPUT_CLASS} type="number" min={1} value={gold} onChange={(event) => setGold(Number(event.target.value))} />
        </FormField>
      ) : null}
      {kind === "pact" ? (
        <FormField label="Turns">
          <input className={FORM_INPUT_CLASS} type="number" min={1} value={pactTurns} onChange={(event) => setPactTurns(Number(event.target.value))} />
        </FormField>
      ) : null}
      {kind === "claim_cession" && claimed.length > 0 ? (
        <FormField label="Region">
          <select className={FORM_INPUT_CLASS} value={effectiveRegionId} onChange={(event) => setRegionId(event.target.value)}>
            {claimed.map((region) => (
              <option key={region.id} value={region.id}>{region.label}</option>
            ))}
          </select>
        </FormField>
      ) : null}
      {kind === "claim_cession" && claimed.length === 0 ? (
        <p role="status" className="text-[12px] italic text-[#72787c]">This member claims none of your regions.</p>
      ) : null}
    </StrategyFormDialog>
  );
}
