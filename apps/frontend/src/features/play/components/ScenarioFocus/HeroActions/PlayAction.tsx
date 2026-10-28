import React from "react";
import { IconArrowRight } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";

export interface PlayActionProps {
  scenarioId: string;
  isDraft: boolean;
  isStartingPlaytest: boolean;
  onPlaytest: () => void;
}

export const PlayAction: React.FC<PlayActionProps> = ({
  scenarioId,
  isDraft,
  isStartingPlaytest,
  onPlaytest,
}) => {
  if (isDraft) {
    return (
      <Button
        variant="primary"
        size="lg"
        onClick={onPlaytest}
        disabled={isStartingPlaytest}
        className="w-full sm:w-auto font-display font-bold"
      >
        <span>{isStartingPlaytest ? "Starting…" : "Playtest"}</span>
        <IconArrowRight size={18} stroke={1.5} aria-hidden="true" />
      </Button>
    );
  }

  return (
    <ButtonLink
      to={`/setup/${scenarioId}`}
      variant="primary"
      size="lg"
      className="w-full sm:w-auto font-display font-bold"
    >
      <span>Play</span>
      <IconArrowRight size={18} stroke={1.5} aria-hidden="true" />
    </ButtonLink>
  );
};
