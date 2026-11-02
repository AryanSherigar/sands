import React from "react";
import type { TreatyTerm } from "../../../../types/scene.types";
import type { NegotiationTreatyDrawerProps } from "./NegotiationTreatyDrawer.types";
import { TreatyTermCard } from "./TreatyTermCard";
import { describeTreatyTerm } from "./treatyTermViews";
import { VerdictNote } from "./VerdictNote";

const DEFAULT_TIER_TURNS: Record<string, number> = {
  short: 6,
  medium: 16,
  generation: 60,
};

const renderTermCard = (term: TreatyTerm, idx: number, currentTurn: number) => {
  switch (term.kind) {
    case "peace": {
      const tierLabel = term.tier.charAt(0).toUpperCase() + term.tier.slice(1);
      const durationTurns = term.duration_turns ?? DEFAULT_TIER_TURNS[term.tier];
      const durationText =
        term.tier === "perpetual" || !durationTurns
          ? "Perpetual peace covenant between both realms."
          : `Binds peace for ${durationTurns} turns (ending turn ${currentTurn + durationTurns}).`;
      const guarantors =
        term.guarantor_ids && term.guarantor_ids.length > 0
          ? `Guarantors: ${term.guarantor_ids.join(", ")}`
          : null;

      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-meadow-green shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-meadow-green">
                handshake
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Peace Treaty
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-primary-fixed text-on-primary-fixed font-bold rounded">
              {tierLabel}
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">{durationText}</p>
          {guarantors && (
            <p className="font-sans text-[11px] text-outline/80 mt-1 ml-4 italic">
              {guarantors}
            </p>
          )}
        </div>
      );
    }
    case "pay_gold": {
      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-amber-500">
                payments
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Indemnity Payment
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-amber-500/20 text-amber-300 font-bold rounded">
              Payment
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">
            Lump sum indemnity of {term.amount}g from {term.payer_id} to {term.payee_id}.
          </p>
        </div>
      );
    }
    case "tribute": {
      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-amber-500">
                hourglass_bottom
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Annual Tribute
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-amber-500/20 text-amber-300 font-bold rounded">
              Tribute
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">
            Annual tribute commitment of {term.gold_per_turn}g for {term.duration_turns} turns
            (ending turn {currentTurn + term.duration_turns}).
          </p>
        </div>
      );
    }
    case "cede_region": {
      const targetFaction = term.to_faction_id ?? term.to_faction ?? "the victor";
      const regionName = term.region_name ?? term.region_id;
      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#A8483E] shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-[#A8483E]">
                flag
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Ceded Territory
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-[#A8483E]/20 text-rose-300 font-bold rounded">
              Cession
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">
            Cede sovereignty of {regionName} to {targetFaction}.
          </p>
        </div>
      );
    }
    case "release_prisoners": {
      const prisonerCount = term.prisoner_ids?.length ?? term.character_ids?.length;
      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500 shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-sky-500">
                lock_open
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Release Prisoners
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-sky-500/20 text-sky-300 font-bold rounded">
              Prisoners
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">
            Released prisoners{prisonerCount ? ` (${prisonerCount})` : ""}
            {term.ransom_gold ? ` with ransom of ${term.ransom_gold}g` : ""}.
          </p>
        </div>
      );
    }
    case "hostage": {
      const hostageName =
        term.character_name ?? term.leader_id ?? term.character_id ?? "court noble";
      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-purple-500">
                shield_person
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Hostage Pledge
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-purple-500/20 text-purple-300 font-bold rounded">
              Hostage
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">
            Hostage pledge: {hostageName}
            {term.duration_turns
              ? ` for ${term.duration_turns} turns (ending turn ${currentTurn + term.duration_turns})`
              : ""}
            .
          </p>
        </div>
      );
    }
    case "non_aggression": {
      return (
        <div
          key={idx}
          className="p-3.5 bg-surface-container rounded-xl shadow-sm border border-outline-variant/30"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-meadow-green shrink-0" />
              <span className="material-symbols-outlined text-[18px] text-meadow-green">
                handshake
              </span>
              <span className="font-serif text-base font-semibold text-on-surface">
                Non-Aggression Pact
              </span>
            </div>
            <span className="font-sans text-[10px] uppercase px-2 py-0.5 bg-primary-fixed text-on-primary-fixed font-bold rounded">
              Proposed
            </span>
          </div>
          <p className="font-sans text-xs text-outline mt-1.5 ml-4">
            Binds both realms for {term.duration_turns} turns (ending turn{" "}
            {currentTurn + term.duration_turns}).
          </p>
        </div>
      );
    }
    default:
      return <TreatyTermCard key={idx} view={describeTreatyTerm(term, currentTurn)} />;
  }
};

export const NegotiationTreatyDrawer: React.FC<NegotiationTreatyDrawerProps> = ({
  isOpen,
  proposal,
  currentTurn,
  counterpartName,
  isBusy = false,
  verdict = null,
  onClose,
  onSign,
  onDecline,
}) => {
  return (
    <aside
      className={`absolute right-0 top-0 bottom-0 w-96 bg-parchment-panel/95 backdrop-blur-md shadow-2xl p-6 flex flex-col justify-between transition-transform duration-300 ease-in-out z-30 border-l border-outline-variant/30 ${
        isOpen ? "translate-x-0" : "translate-x-full"
      }`}
      role="complementary"
      aria-label="Treaty Drawer"
      aria-expanded={isOpen}
    >
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-outline-variant/20">
          <div className="flex items-center gap-2 text-primary font-serif text-xl font-semibold">
            <span className="material-symbols-outlined text-[24px]">balance</span>
            <span>On the Table</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-outline hover:text-on-surface hover:bg-surface-variant/40 transition-colors cursor-pointer"
            aria-label="Close drawer"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <p className="font-sans text-xs text-outline my-4">
          Current conditions and sovereign covenants debated with {counterpartName}.
        </p>

        <VerdictNote verdict={verdict} hasProposal={Boolean(proposal)} />

        {proposal && proposal.terms.length > 0 ? (
          <div className="space-y-3">
            {proposal.terms.map((term, idx) => renderTermCard(term, idx, currentTurn))}
          </div>
        ) : (
          <div className="p-6 text-center text-outline font-sans text-sm italic bg-surface-container/40 rounded-xl border border-outline-variant/20">
            No terms currently drafted on the parchment. Speak to propose terms.
          </div>
        )}
      </div>

      <div className="space-y-3 pt-4 border-t border-outline-variant/20">
        <div className="bg-surface-container-lowest/60 p-3 rounded-lg border border-outline-variant/20">
          <p className="font-sans text-[11px] italic text-outline leading-snug">
            Nothing is binding until you sign under royal seal.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <button
            type="button"
            disabled={!proposal || isBusy}
            onClick={onSign}
            aria-label="Sign the pact"
            className="w-full py-2.5 px-4 bg-secondary-container hover:bg-secondary-fixed text-on-secondary-container font-sans text-sm font-semibold rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">history_edu</span>
            <span>Sign the Pact</span>
          </button>

          {onDecline ? (
            <button
              type="button"
              disabled={isBusy}
              onClick={onDecline}
              className="w-full py-2 px-4 bg-surface-container-high hover:bg-surface-variant text-on-surface font-sans text-xs font-semibold rounded-xl transition-all cursor-pointer disabled:opacity-40"
            >
              Decline Offer
            </button>
          ) : null}
        </div>
      </div>
    </aside>
  );
};
