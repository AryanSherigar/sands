import React from "react";
import { IconBook, IconPlayerPlayFilled } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { SCENARIO_PATH_PREFIX } from "../constants/landing.constants";
import { usePlayScenario } from "../hooks/usePlayScenario";
import { getGenreColor } from "../utils/getGenreColor";
import type { HeroActionsProps } from "./HeroActions.types";

export const HeroActions: React.FC<HeroActionsProps> = ({
  scenarioId,
  primaryGenre,
}) => {
  const handlePlay = usePlayScenario(scenarioId);
  const genreColor = getGenreColor(primaryGenre);

  return (
    <div className="mt-6 flex flex-col gap-3 sm:flex-row">
      <Button
        variant="ghost"
        size="lg"
        className="border bg-black hover:bg-black/80"
        style={{ borderColor: genreColor, color: genreColor }}
        onClick={handlePlay}
      >
        <IconPlayerPlayFilled size={18} stroke={1.5} />
        Play now
      </Button>
      <ButtonLink
        to={`${SCENARIO_PATH_PREFIX}/${scenarioId}`}
        variant="secondary"
        size="lg"
      >
        <IconBook size={18} stroke={1.5} />
        View scenario
      </ButtonLink>
    </div>
  );
};

