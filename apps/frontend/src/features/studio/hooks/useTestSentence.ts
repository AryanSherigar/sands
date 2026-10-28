import { useCallback } from "react";
import { PLAYTEST_CARD_VALUES_NOTE_PREFIX } from "../constants/playtest";
import { listCardValueLabels, overridesForSentence } from "../lib/stateOverrides";
import { usePlaytestStore } from "../stores/playtest.store";
import type { Sentence } from "../types/sentence.types";
import { useOpenPlaytestTab } from "./useOpenPlaytestTab";
import { useValueOptions } from "./useValueOptions";

interface TestSentenceRequest {
  kind: "ending" | "rule";
  sentence: Sentence | null;
}

export type TestSentence = (request: TestSentenceRequest) => void;

export const useTestSentence = (): TestSentence => {
  const options = useValueOptions();
  const requestTest = usePlaytestStore((state) => state.requestTest);
  const openPlaytestTab = useOpenPlaytestTab();

  return useCallback(
    ({ sentence }: TestSentenceRequest): void => {
      const overrides = sentence ? overridesForSentence(sentence, options) : {};
      const cardLabels = sentence ? listCardValueLabels(sentence, options) : [];
      const note =
        cardLabels.length > 0
          ? `${PLAYTEST_CARD_VALUES_NOTE_PREFIX} ${cardLabels.join(", ")}.`
          : null;
      requestTest({ overrides, note });
      openPlaytestTab();
    },
    [openPlaytestTab, options, requestTest],
  );
};
