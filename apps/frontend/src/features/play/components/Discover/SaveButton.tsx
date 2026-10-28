import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { SaveButtonProps } from "./SaveButton.types";

export const SaveButton: React.FC<SaveButtonProps> = ({
  scenario,
  onToggleSave,
}) => {
  const handleClick = (event: React.MouseEvent): void => {
    event.stopPropagation();
    onToggleSave(scenario);
  };

  return (
    <Button
      variant="secondary"
      size="sm"
      aria-pressed={scenario.is_bookmarked}
      aria-label={`${scenario.is_bookmarked ? "Saved" : "Save"}: ${scenario.title}`}
      onClick={handleClick}
    >
      {scenario.is_bookmarked ? "Saved" : "Save"}
    </Button>
  );
};
