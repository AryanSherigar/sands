import React, { useMemo } from "react";
import { Button } from "@/shared/components/ui/Button";
import { OPENING_DOCUMENT_KEY } from "../../constants/opening";
import { OPENING_QUESTION_GROUPS } from "../../constants/guideQuestions";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";
import { useGuideCards } from "../../hooks/useGuideCards";
import { useWorldDocument } from "../../hooks/useWorldDocument";
import { getCardKind } from "../../lib/cardKind";
import { insertPlayerNameToken } from "../../lib/openingToken";
import type { PickOption } from "../../types/guide.types";
import { LoreBox } from "../LoreBox/LoreBox";
import { PlayerNameChipPreview } from "./PlayerNameChipPreview";
import { PlayOpeningButton } from "./PlayOpeningButton";
import { StartsAtPicker } from "./StartsAtPicker";

const OPENING_PLACEHOLDER = "Rain on the pier. The last ferry has just left, and someone is waiting.";

export const OpeningSection: React.FC = () => {
  const opening = useWorldDocument(OPENING_DOCUMENT_KEY);
  const { entities } = useGuideCards();
  const { addLine } = useAlwaysRemember();
  const pickOptions = useMemo(
    (): PickOption[] =>
      entities
        .filter((entity) => !entity.is_player)
        .map((entity) => ({
          id: entity.entity_id,
          name: entity.canonical_name,
          kind: getCardKind(entity.entity_type),
        })),
    [entities],
  );
  const places = useMemo(() => pickOptions.filter((option) => option.kind === "place"), [pickOptions]);

  const handleInsertName = (): void => opening.onChange(insertPlayerNameToken(opening.document));

  return (
    <div className="space-y-3">
      <LoreBox
        document={opening.document}
        onChange={opening.onChange}
        questions={OPENING_QUESTION_GROUPS}
        pickOptions={pickOptions}
        ariaLabel="Opening scene"
        placeholder={OPENING_PLACEHOLDER}
        onAddToAlwaysRemember={addLine}
      />
      <PlayerNameChipPreview document={opening.document} />
      <div className="flex flex-wrap items-end gap-4">
        <Button type="button" variant="secondary" size="sm" onClick={handleInsertName}>
          Insert player's name
        </Button>
        <div className="min-w-[12rem] flex-1">
          <StartsAtPicker document={opening.document} places={places} onChange={opening.onChange} />
        </div>
      </div>
      <PlayOpeningButton document={opening.document} />
    </div>
  );
};
