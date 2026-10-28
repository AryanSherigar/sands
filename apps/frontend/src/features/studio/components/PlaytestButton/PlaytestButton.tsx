import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/shared/components/ui/Button";
import { buildPlaytestSetupPath } from "@/shared/constants/navigation";
import { PlaytestButtonProps } from "./PlaytestButton.types";

export const PlaytestButton: React.FC<PlaytestButtonProps> = ({
  scenarioId,
}) => {
  const navigate = useNavigate();

  const handlePlaytest = (): void => {
    navigate(buildPlaytestSetupPath(scenarioId));
  };

  return (
    <Button variant="secondary" onClick={handlePlaytest}>
      Playtest
    </Button>
  );
};
