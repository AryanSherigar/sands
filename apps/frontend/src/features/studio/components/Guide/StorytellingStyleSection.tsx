import React from "react";
import { STYLE_QUESTION_GROUPS } from "../../constants/guideQuestions";
import { useGuide } from "../../hooks/useGuide";
import { useServerSyncedState } from "../../hooks/useServerSyncedState";
import { EMPTY_LORE_DOCUMENT } from "../../lib/worldDocuments";
import type { LoreDocument } from "../../types/lore.types";
import { LoreBox } from "../LoreBox/LoreBox";
import { StyleChips } from "./StyleChips";

const STYLE_PLACEHOLDER = "Describe how the narrator should write. Leave it empty for the default voice.";

export const StorytellingStyleSection: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const [local, setLocal] = useServerSyncedState<LoreDocument>(
    scenario?.narrator_persona_document ?? EMPTY_LORE_DOCUMENT,
  );
  const document = local ?? EMPTY_LORE_DOCUMENT;

  const handleChange = (next: LoreDocument): void => {
    setLocal(next);
    saveFields({ narrator_persona_document: next });
  };

  return (
    <section aria-labelledby="storytelling-style" className="space-y-3">
      <div className="space-y-1">
        <h3 id="storytelling-style" className="text-heading font-semibold text-content">
          How should the story be told?
        </h3>
        <p className="text-meta text-content-muted">This guides how the narrator writes, every turn.</p>
      </div>
      <StyleChips document={document} onChange={handleChange} />
      <LoreBox
        document={document}
        onChange={handleChange}
        questions={STYLE_QUESTION_GROUPS}
        ariaLabel="Storytelling style"
        placeholder={STYLE_PLACEHOLDER}
      />
    </section>
  );
};
