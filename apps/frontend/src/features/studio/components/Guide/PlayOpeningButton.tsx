import React from "react";
import { IconPlayerPlay } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { useOpenPlaytestTab } from "../../hooks/useOpenPlaytestTab";
import { countWords } from "../../lib/loreDocument";
import type { PlayOpeningButtonProps } from "./Guide.types";

export const PlayOpeningButton: React.FC<PlayOpeningButtonProps> = ({ document }) => {
  const handlePlay = useOpenPlaytestTab();
  const hasText = countWords(document) > 0;


  return (
    <Button type="button" size="lg" className="w-full" disabled={!hasText} onClick={handlePlay}>
      <IconPlayerPlay size={18} aria-hidden="true" className="mr-2" />
      Play your opening
    </Button>
  );
};
