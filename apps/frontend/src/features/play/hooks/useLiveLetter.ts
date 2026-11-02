import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSceneView } from "../api/scene.api";
import {
  LETTER_DECLINED_MESSAGE,
  LETTER_OUTCOME_TEXT,
  LETTER_SCENE_TYPE,
} from "../constants/letter.constants";
import {
  FINAL_SCENE_STATUSES,
  getSceneQueryKey,
} from "../constants/scene.constants";
import { buildLetterPackage } from "../lib/letter-package";
import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import type {
  LetterSealSubmission,
  StrategyLetterPackage,
} from "../types/letterScene.types";
import type { SceneViewResponse } from "../types/scene.types";
import { useLetterSceneStream } from "./useLetterSceneStream";
import { useSceneDecision } from "./useSceneDecision";
import { useSceneView } from "./useSceneView";
import { getWorldQueryKey } from "./useSimulationCommands";

interface LiveLetterWorld {
  status: string;
  scene_id?: string | null;
}

interface OpenedLetter {
  sceneId: string;
  text: string;
}

const describeOutcome = (view: SceneViewResponse): string | null => {
  if (view.outcome?.kind !== "choice") return null;
  return LETTER_OUTCOME_TEXT[view.outcome.option_id] ?? null;
};

function useLetterSource(playthroughId: string | undefined, world: LiveLetterWorld) {
  const pendingSceneId = world.status === "awaiting_scene" ? (world.scene_id ?? null) : null;
  const query = useSceneView(playthroughId, pendingSceneId);
  const view = query.data;
  const isLetterScene =
    view !== undefined &&
    view.scene_type === LETTER_SCENE_TYPE &&
    !FINAL_SCENE_STATUSES.includes(view.status);
  return {
    view,
    sceneId: isLetterScene ? view.scene_id : null,
    isLetterScene,
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

export function useLiveLetter(playthroughId: string | undefined, world: LiveLetterWorld) {
  const queryClient = useQueryClient();
  const setOrderFeedback = useStrategyPlayStore((state) => state.setOrderFeedback);
  const { view, sceneId, isLetterScene, isSceneTypeResolved } = useLetterSource(
    playthroughId,
    world,
  );
  const stream = useLetterSceneStream(sceneId, useRefreshAfterExchange(playthroughId, sceneId));
  const [shelvedSceneId, setShelvedSceneId] = useState<string | null>(null);
  const [openedLetter, setOpenedLetter] = useState<OpenedLetter | null>(null);
  const requestedSceneIds = useRef(new Set<string>());

  const storedText = view?.transcript[0]?.leader_text ?? "";
  const localText = openedLetter?.sceneId === sceneId ? openedLetter.text : "";
  const liveText = stream.isStreaming ? stream.streamedText : "";
  const incomingText = storedText || localText || liveText;

  const startOpen = useCallback((): void => {
    if (!sceneId || stream.isStreaming) return;
    void stream.openLetter().then((text) => {
      if (text) setOpenedLetter({ sceneId, text });
    });
  }, [sceneId, stream]);

  useEffect(() => {
    const isUnopened = view !== undefined && view.transcript.length === 0;
    if (!sceneId || !isUnopened || requestedSceneIds.current.has(sceneId)) return;
    requestedSceneIds.current.add(sceneId);
    startOpen();
  }, [sceneId, view, startOpen]);

  const pkg: StrategyLetterPackage | null = useMemo(
    () => (view && sceneId && incomingText ? buildLetterPackage(view, incomingText) : null),
    [view, sceneId, incomingText],
  );

  const { decide } = useSceneDecision(playthroughId, sceneId);

  const handleDecline = useCallback((): void => {
    decide(
      { isConfirmed: false },
      { onSuccess: () => setOrderFeedback({ message: LETTER_DECLINED_MESSAGE }) },
    );
  }, [decide, setOrderFeedback]);

  const handleClose = useCallback(() => setShelvedSceneId(sceneId), [sceneId]);

  const handleOpen = useCallback((): void => {
    setShelvedSceneId(null);
    if (!incomingText) startOpen();
  }, [incomingText, startOpen]);

  const handleSeal = useCallback(
    async (submission: LetterSealSubmission): Promise<boolean> => {
      const isSent = await stream.sealLetter(submission.finalProse);
      if (!isSent || !playthroughId || !sceneId) return isSent;
      const finished = await queryClient.fetchQuery({
        queryKey: getSceneQueryKey(playthroughId, sceneId),
        queryFn: () => getSceneView(playthroughId, sceneId),
        staleTime: 0,
      });
      const message = describeOutcome(finished);
      if (message) setOrderFeedback({ message });
      return true;
    },
    [stream, playthroughId, sceneId, queryClient, setOrderFeedback],
  );

  const isOpen = pkg !== null && shelvedSceneId !== sceneId;

  return {
    pkg,
    isOpen,
    isLetterScene,
    isSceneTypeResolved,
    dispatchNumber: isLetterScene && view && !isOpen ? view.turn : undefined,
    failureMessage: stream.failureMessage,
    handleOpen,
    handleClose,
    handleSeal,
    handleDecline,
    requestScribeDraft: stream.requestScribeDraft,
  };
}
