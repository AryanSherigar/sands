import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { SceneTermsCardProps } from "./SceneTermsCard.types";

export const SceneTermsCard: React.FC<SceneTermsCardProps> = ({
  card,
  counterpartName,
  currentTurn,
  isBusy,
  onConfirm,
  onDecline,
}) => {
  return (
    <section
      aria-label="Proposed terms"
      className="flex flex-col gap-2 rounded-md border border-accent/40 bg-accent/5 p-3"
    >
      <span className="text-micro font-semibold uppercase tracking-wide text-accent">
        Terms on the table
      </span>
      <ul className="flex flex-col gap-1 text-sm text-content">
        {card.terms.map((term) => (
          <li key={`${term.kind}-${term.faction_a}-${term.faction_b}`}>
            A non-aggression pact with {counterpartName} for {term.duration_turns} turns,
            ending on turn {currentTurn + term.duration_turns}.
          </li>
        ))}
      </ul>
      <p className="text-micro text-content-muted">
        Nothing is binding until you sign.
      </p>
      <div className="flex gap-2">
        <Button size="sm" disabled={isBusy} onClick={onConfirm}>
          Sign the pact
        </Button>
        {onDecline ? (
          <Button size="sm" variant="ghost" disabled={isBusy} onClick={onDecline}>
            Decline
          </Button>
        ) : null}
      </div>
    </section>
  );
};
