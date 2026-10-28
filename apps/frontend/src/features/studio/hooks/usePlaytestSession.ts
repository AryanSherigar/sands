import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { startPlaytest } from "@/shared/api/playthroughs.api";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { logEvent } from "@/shared/lib/logger";
import { PLAYTEST_START_FAILED_MESSAGE } from "../constants/playtest";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { getErrorStatus } from "../lib/errorStatus";
import { readOpeningText } from "../lib/playtestSetup";
import { usePlaytestStore } from "../stores/playtest.store";
import type { ScenarioResponse } from "../types/scenario.types";
import { useGuide } from "./useGuide";

const UNPROCESSABLE_STATUS = 422;

interface PlaytestStartOptions {
  overrides?: Record<string, unknown>;
  note?: string | null;
}

export const usePlaytestSession = () => {
  const queryClient = useQueryClient();
  const { scenarioId, flushSaves } = useGuide();
  const beginSession = usePlaytestStore((state) => state.beginSession);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const start = async (
    setupValues: Record<string, unknown>,
    options: PlaytestStartOptions = {},
  ): Promise<void> => {
    if (!scenarioId || isStarting) return;
    setIsStarting(true);
    setStartError(null);
    try {
      await flushSaves();
      const playthrough = await startPlaytest(scenarioId, setupValues, options.overrides);
      const scenario = queryClient.getQueryData<ScenarioResponse>([SCENARIO_QUERY_KEY, scenarioId]);
      beginSession({
        scenarioId,
        playthroughId: playthrough.playthrough_id,
        participantId: playthrough.participant_id,
        openingText: readOpeningText(playthrough),
        startedStamp: scenario?.content_edited_at ?? null,
        setupValues,
        state: playthrough.state ?? {},
        note: options.note ?? null,
      });
    } catch (error) {
      const isRejectedPreset = getErrorStatus(error) === UNPROCESSABLE_STATUS;
      setStartError(
        isRejectedPreset
          ? extractErrorMessage(error, PLAYTEST_START_FAILED_MESSAGE)
          : PLAYTEST_START_FAILED_MESSAGE,
      );
      logEvent("warning", "playtest_start_failed", { error: String(error) });
    } finally {
      setIsStarting(false);
    }
  };

  return { start, isStarting, startError };
};
