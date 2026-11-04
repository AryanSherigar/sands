import React, { useState } from "react";
import { buildRealmAffairGroups, type RealmAffairAction, type RealmAffairForm } from "../../../lib/realmAffairs";
import { AppeaseForm } from "./AppeaseForm";
import { SubsidizeForm } from "./SubsidizeForm";
import { GrantConsentForm } from "./GrantConsentForm";
import { VassalDemandForm } from "./VassalDemandForm";
import type { CampaignWorldView, StrategyOrder } from "../../../types/simulation.types";
import { StrategyConfirmDialog } from "../ui/StrategyConfirmDialog";

export interface RealmAffairsSectionProps {
  world: CampaignWorldView;
  onSubmitOrder?: (order: StrategyOrder) => void;
  regionNames?: Record<string, string>;
}

const ACTION_CLASS =
  "rounded bg-[#46606E] px-2 py-0.5 text-[11px] font-bold text-white hover:bg-[#3A5260] cursor-pointer transition";

export const RealmAffairsSection: React.FC<RealmAffairsSectionProps> = ({ world, onSubmitOrder, regionNames }) => {
  const [pending, setPending] = useState<RealmAffairAction | null>(null);
  const [activeForm, setActiveForm] = useState<RealmAffairForm | null>(null);
  const groups = buildRealmAffairGroups(world, regionNames);
  if (groups.length === 0) return null;

  const handleSubmitForm = (order: StrategyOrder): void => {
    setActiveForm(null);
    onSubmitOrder?.(order);
  };

  const handleAction = (action: RealmAffairAction): void => {
    if (action.form) {
      setActiveForm(action.form);
      return;
    }
    if (action.confirmation) {
      setPending(action);
      return;
    }
    if (action.order) onSubmitOrder?.(action.order);
  };

  const handleConfirm = (): void => {
    if (pending?.order) onSubmitOrder?.(pending.order);
    setPending(null);
  };

  return (
    <section aria-label="Realm affairs" className="flex flex-col gap-2">
      <span className="text-[10px] font-bold uppercase tracking-wider text-[#46606E]">Realm affairs</span>
      {groups.map((group) => (
        <div key={group.id} className="flex flex-col gap-1.5">
          <h3 className="text-[11px] font-semibold text-[#42474b]">{group.heading}</h3>
          {group.affairs.map((affair) => (
            <div key={affair.id} className="flex flex-col gap-1 rounded-lg border border-[#3A3128]/10 bg-[#F5E5D8]/70 p-2">
              <span className="text-xs font-bold text-[#221A12]">{affair.title}</span>
              <span className="text-[10px] text-[#72787C]">{affair.detail}</span>
              {affair.actions.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {affair.actions.map((action) => (
                    <button key={action.label} type="button" className={ACTION_CLASS} onClick={() => handleAction(action)}>
                      {action.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ))}
      <StrategyConfirmDialog
        isOpen={pending !== null}
        title={pending?.confirmation?.title ?? ""}
        message={pending?.confirmation?.message ?? ""}
        confirmLabel={pending?.confirmation?.confirmLabel ?? "Confirm"}
        onConfirm={handleConfirm}
        onCancel={() => setPending(null)}
      />
      {activeForm?.kind === "subsidize" ? (
        <SubsidizeForm factionId={world.my_faction.id} warId={activeForm.warId} receivers={activeForm.receivers} onSubmit={handleSubmitForm} onCancel={() => setActiveForm(null)} />
      ) : null}
      {activeForm?.kind === "appease" ? (
        <AppeaseForm factionId={world.my_faction.id} members={activeForm.members} claimedRegionsByMember={activeForm.claimedRegionsByMember} onSubmit={handleSubmitForm} onCancel={() => setActiveForm(null)} />
      ) : null}
      {activeForm?.kind === "grant_consent" ? (
        <GrantConsentForm factionId={world.my_faction.id} vassalageId={activeForm.vassalageId} targets={activeForm.targets} onSubmit={handleSubmitForm} onCancel={() => setActiveForm(null)} />
      ) : null}
      {activeForm?.kind === "vassal_demand" ? (
        <VassalDemandForm factionId={world.my_faction.id} vassalageId={activeForm.vassalageId} tributePercent={activeForm.tributePercent} levyPercent={activeForm.levyPercent} onSubmit={handleSubmitForm} onCancel={() => setActiveForm(null)} />
      ) : null}
    </section>
  );
};
