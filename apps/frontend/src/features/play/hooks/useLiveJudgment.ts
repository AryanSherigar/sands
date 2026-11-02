import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSceneView } from "../api/scene.api";
import {
  DEFAULT_JUDGMENT_VERDICT,
  JUDGMENT_SCENE_TYPE,
} from "../constants/judgment.constants";
import { FINAL_SCENE_STATUSES, getSceneQueryKey } from "../constants/scene.constants";
import { buildJudgmentPackage } from "../lib/judgment-package";
import type {
  JudgmentPronouncement,
  StrategyJudgmentPackage,
} from "../types/judgmentScene.types";
import { useJudgmentSceneStream } from "./useJudgmentSceneStream";
import { useSceneView } from "./useSceneView";
import { getWorldQueryKey } from "./useSimulationCommands";

interface LiveJudgmentWorld {
  status: string;
  scene_id?: string | null;
}

const IMPRISON_ON_LEAVING: JudgmentPronouncement = {
  verdict: DEFAULT_JUDGMENT_VERDICT,
  nuance: null,
  decreeText: "",
};

function useJudgmentSource(playthroughId: string | undefined, world: LiveJudgmentWorld) {
  const pendingSceneId = world.status === "awaiting_scene" ? (world.scene_id ?? null) : null;
  const query = useSceneView(playthroughId, pendingSceneId);
  const view = query.data;
  const isJudgmentScene =
    view !== undefined &&
    view.scene_type === JUDGMENT_SCENE_TYPE &&
    !FINAL_SCENE_STATUSES.includes(view.status);
  return {
    view,
    sceneId: isJudgmentScene ? view.scene_id : null,
    isJudgmentScene,
    isSceneTypeResolved: !pendingSceneId || query.isFetched,
  };
}

function useRefreshAfterExchange(playthroughId: string | undefined, sceneId: string | null) {
  const queryClient = useQueryClient();
  return useCallback(
    () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: getSceneQueryKey(playthroughId, sceneId) }),
        queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) }),
      ]),
    [queryClient, playthroughId, sceneId],
  );
}

export function useLiveJudgment(playthroughId: string | undefined, world: LiveJudgmentWorld) {
  const queryClient = useQueryClient();
  const { view, sceneId, isJudgmentScene, isSceneTypeResolved } = useJudgmentSource(
    playthroughId,
    world,
  );
  const stream = useJudgmentSceneStream(
    sceneId,
    useRefreshAfterExchange(playthroughId, sceneId),
  );
  const [revealed, setRevealed] = useState<StrategyJudgmentPackage | null>(null);
  const requestedSceneIds = useRef(new Set<string>());

  const livePackage = useMemo(
    () => (view && isJudgmentScene ? buildJudgmentPackage(view, stream.streamedText) : null),
    [view, isJudgmentScene, stream.streamedText],
  );

  useEffect(() => {
    const isUnopened = view !== undefined && view.transcript.length === 0;
    if (!sceneId || !isUnopened || requestedSceneIds.current.has(sceneId)) return;
    requestedSceneIds.current.add(sceneId);
    void stream.openCourt();
  }, [sceneId, view, stream]);

  const handleSpeak = useCallback(
    (text: string): Promise<boolean> => stream.speak(text),
    [stream],
  );

  const handlePronounce = useCallback(
    async (pronouncement: JudgmentPronouncement): Promise<boolean> => {
      const isDone = await stream.pronounce(pronouncement);
      if (!isDone || !playthroughId || !sceneId) return isDone;
      const finished = await queryClient.fetchQuery({
        queryKey: getSceneQueryKey(playthroughId, sceneId),
        queryFn: () => getSceneView(playthroughId, sceneId),
        staleTime: 0,
      });
      setRevealed(buildJudgmentPackage(finished));
      return true;
    },
    [stream, playthroughId, sceneId, queryClient],
  );

  const canRetryOpen =
    stream.failureMessage !== null && view !== undefined && view.transcript.length === 0;

  const handleRetryOpen = useCallback((): void => {
    if (!sceneId) return;
    requestedSceneIds.current.add(sceneId);
    void stream.openCourt();
  }, [sceneId, stream]);

  const handleDismissReveal = useCallback((): void => setRevealed(null), []);

  const handleClose = useCallback((): void => {
    if (revealed) {
      handleDismissReveal();
      return;
    }
    void handlePronounce(IMPRISON_ON_LEAVING);
  }, [revealed, handleDismissReveal, handlePronounce]);

  const pkg = revealed ?? livePackage;

  return {
    pkg,
    isOpen: pkg !== null,
    isJudgmentScene,
    isSceneTypeResolved,
    isStreaming: stream.isStreaming,
    liveText: stream.isStreaming ? stream.streamedText : "",
    failureMessage: stream.failureMessage,
    canRetryOpen,
    handleRetryOpen,
    handleSpeak,
    handlePronounce,
    handleDismissReveal,
    handleClose,
  };
}
