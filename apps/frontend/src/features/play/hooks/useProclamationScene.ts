import { useState, useCallback, useMemo, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { buildOperationGuard } from "../lib/operationGuard";
import { readCachedWorld } from "./useSimulationCommands";
import {
  classifyProclamation,
  conveneProclamationCouncil,
  decideProclamation,
  streamCouncilDialogue,
  type ProclamationDraft,
  type ProclamationScenePackage,
  type ActiveProclamation,
} from "../api/proclamation.api";

import {
  parseCouncilReply,
  SOVEREIGN_SPEAKER,
  type CouncilDialogueLine,
} from "../lib/proclamation-lines";

export type { CouncilDialogueLine };

type TranscriptSegment =
  | { kind: "sovereign"; text: string }
  | { kind: "council"; raw: string };

const toDialogueLines = (segment: TranscriptSegment): CouncilDialogueLine[] =>
  segment.kind === "sovereign"
    ? [{ speaker: SOVEREIGN_SPEAKER, text: segment.text }]
    : parseCouncilReply(segment.raw);

const appendCouncilChunk = (
  segments: TranscriptSegment[],
  chunk: string,
): TranscriptSegment[] => {
  const last = segments[segments.length - 1];
  if (last?.kind === "council") {
    return [...segments.slice(0, -1), { kind: "council", raw: last.raw + chunk }];
  }
  return [...segments, { kind: "council", raw: chunk }];
};

export function useProclamationScene(playthroughId?: string) {
  const queryClient = useQueryClient();
  const [isDraftOpen, setIsDraftOpen] = useState(false);
  const [isCouncilOpen, setIsCouncilOpen] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [isClassifying, setIsClassifying] = useState(false);
  const [isEnacting, setIsEnacting] = useState(false);
  const [localEdict, setLocalEdict] = useState<ActiveProclamation | null>(null);
  const [currentDraft, setCurrentDraft] = useState<ProclamationDraft | null>(null);
  const [councilPackage, setCouncilPackage] = useState<ProclamationScenePackage | null>(null);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const transcript = useMemo(() => segments.flatMap(toDialogueLines), [segments]);
  const [isStreaming, setIsStreaming] = useState(false);
  const cancelStreamRef = useRef<(() => void) | null>(null);

  const openDraft = useCallback(() => {
    setDraftError(null);
    setIsDraftOpen(true);
  }, []);

  const closeDraft = useCallback(() => {
    setIsDraftOpen(false);
  }, []);

  const closeCouncil = useCallback(() => {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setIsCouncilOpen(false);
    setIsStreaming(false);
  }, []);

  const _appendStreamText = useCallback((chunk: string) => {
    setSegments((previous) => appendCouncilChunk(previous, chunk));
  }, []);

  const submitDraft = useCallback(
    async (text: string, isRescinding: boolean = false) => {
      const targetId = playthroughId || "preview-playthrough";
      setIsClassifying(true);
      setDraftError(null);
      try {
        const draft = await classifyProclamation(text);
        if (!draft.is_recognized) {
          setDraftError(
            "The Chancellor shakes his head in dismay: 'Sire, your words lack clarity for the law. The Great Seal cannot be set to confusion.' Speak your will clearly so the scribes may write."
          );
          setIsClassifying(false);
          return;
        }
        setCurrentDraft(draft);
        const pkg = await conveneProclamationCouncil(targetId, draft, isRescinding);
        setCouncilPackage(pkg);
        setIsDraftOpen(false);
        setIsCouncilOpen(true);
        setSegments([]);
        setIsStreaming(true);

        cancelStreamRef.current = streamCouncilDialogue(
          draft,
          { turn: 1 },
          undefined,
          {
            onChunk: (chunk) => _appendStreamText(chunk),
            onDone: () => setIsStreaming(false),
            onError: () => setIsStreaming(false),
          }
        );
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to convene council";
        setDraftError(message);
      } finally {
        setIsClassifying(false);
      }
    },
    [playthroughId, _appendStreamText]
  );

  const sendAddress = useCallback(
    (speech: string) => {
      if (!currentDraft) return;
      setIsStreaming(true);
      setSegments((previous) => [...previous, { kind: "sovereign", text: speech }]);
      if (cancelStreamRef.current) {
        cancelStreamRef.current();
      }
      cancelStreamRef.current = streamCouncilDialogue(
        currentDraft,
        { turn: 1 },
        speech,
        {
          onChunk: (chunk) => _appendStreamText(chunk),
          onDone: () => setIsStreaming(false),
          onError: () => setIsStreaming(false),
        }
      );
    },
    [currentDraft, _appendStreamText]
  );

  const commitDecision = useCallback(
    async (
      verdict: "fiat" | "compromise",
      isRescinding: boolean = false,
      onSuccess?: (edict: ActiveProclamation) => void
    ): Promise<ActiveProclamation | undefined> => {
      const targetId = playthroughId || "preview-playthrough";
      if (!currentDraft) return undefined;
      setIsEnacting(true);
      try {
        const edict = await decideProclamation(
          targetId,
          buildOperationGuard(readCachedWorld(queryClient, targetId)),
          currentDraft,
          verdict,
          isRescinding
        );
        setLocalEdict(edict);
        closeCouncil();
        onSuccess?.(edict);
        return edict;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to enact edict";
        setDraftError(message);
        return undefined;
      } finally {
        setIsEnacting(false);
      }
    },
    [playthroughId, currentDraft, closeCouncil, queryClient]
  );

  return {
    isDraftOpen,
    isCouncilOpen,
    draftError,
    isClassifying,
    isEnacting,
    currentDraft,
    councilPackage,
    transcript,
    isStreaming,
    activeEdict: localEdict,
    openDraft,
    closeDraft,
    closeCouncil,
    submitDraft,
    sendAddress,
    commitDecision,
  };
}
