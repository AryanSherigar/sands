import { createContext } from "react";
import type { AddCardOptions } from "../../hooks/useAddCard";
import type { CardKind } from "../../types/card.types";
import type { ScenarioResponse } from "../../types/scenario.types";
import type { ScenarioFieldsPatch } from "../../types/scenarioPatch.types";

export interface GuideContextValue {
  scenarioId: string | null;
  scenario: ScenarioResponse | null;
  isLoading: boolean;
  saveFields: (patch: ScenarioFieldsPatch) => void;
  ensureDraft: () => Promise<string>;
  hasSaveError: boolean;
  retrySave: () => void;
  flushSaves: () => Promise<void>;
  addCard: (kind: CardKind, options?: AddCardOptions) => void;
}

export const GuideContext = createContext<GuideContextValue | null>(null);
