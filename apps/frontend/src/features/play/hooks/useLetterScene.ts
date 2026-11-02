import { useState, useCallback, useEffect } from "react";
import {
  LETTER_SEAL_MAX_CHARS,
  SCRIBE_FAILED_MESSAGE,
  SCRIBE_INSTRUCTION_MAX_CHARS,
  SCRIBE_INSTRUCTION_TOO_LONG_MESSAGE,
  SCRIBE_UNAVAILABLE_MESSAGE,
  SCRIBE_WORKING_MESSAGE,
  SEAL_EMPTY_MESSAGE,
  SEAL_FAILED_MESSAGE,
  SEAL_TOO_LONG_MESSAGE,
} from "../constants/letter.constants";
import { joinProse, splitProse } from "../lib/letter-prose";
import type {
  DocketChoice,
  DraftRevision,
  LetterSealHandler,
  LetterSealSubmission,
  LetterStage,
  ScribeDraftRequester,
  StrategyLetterPackage,
} from "../types/letterScene.types";

export type { DocketChoice } from "../types/letterScene.types";

const TOAST_DURATION_MS = 2500;
const SEAL_DISPATCH_DELAY_MS = 250;

function isInteractiveInputTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement
  );
}

function buildScribeRevision(
  activeDraft: DraftRevision,
  instruction: string,
  revisionIndex: number,
  prose: string
): DraftRevision {
  return {
    revisionIndex,
    instruction,
    salutation: activeDraft.salutation,
    paragraphs: splitProse(prose),
    signoffText: activeDraft.signoffText,
    authorTitle: activeDraft.authorTitle,
  };
}

function useScribeRequest(
  requestScribeDraft: ScribeDraftRequester | undefined,
  onShowToast: (message: string) => void
) {
  const [isScribeWorking, setIsScribeWorking] = useState(false);

  const requestDraft = useCallback(
    async (instruction: string, currentProse: string): Promise<string | null> => {
      if (!requestScribeDraft) {
        onShowToast(SCRIBE_UNAVAILABLE_MESSAGE);
        return null;
      }
      if (instruction.length > SCRIBE_INSTRUCTION_MAX_CHARS) {
        onShowToast(SCRIBE_INSTRUCTION_TOO_LONG_MESSAGE);
        return null;
      }
      setIsScribeWorking(true);
      onShowToast(SCRIBE_WORKING_MESSAGE);
      try {
        const prose = await requestScribeDraft(instruction, currentProse);
        if (prose.trim()) return prose;
        throw new Error("The scribe returned an empty draft");
      } catch {
        onShowToast(SCRIBE_FAILED_MESSAGE);
        return null;
      } finally {
        setIsScribeWorking(false);
      }
    },
    [requestScribeDraft, onShowToast]
  );

  return { isScribeWorking, requestDraft };
}

function useDraftHistory(
  initialDraft: DraftRevision,
  onRevisionAdded: (message: string) => void,
  requestScribeDraft?: ScribeDraftRequester
) {
  const [history, setHistory] = useState<DraftRevision[]>([initialDraft]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const scribe = useScribeRequest(requestScribeDraft, onRevisionAdded);

  const activeDraft = history[historyIndex] ?? initialDraft;
  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length - 1;

  const handleScribeRewrite = useCallback(
    async (instruction: string): Promise<void> => {
      const prose = await scribe.requestDraft(
        instruction,
        joinProse(activeDraft.paragraphs)
      );
      if (prose === null) return;
      const nextRevision = buildScribeRevision(
        activeDraft,
        instruction,
        historyIndex + 2,
        prose
      );
      const trimmedHistory = history.slice(0, historyIndex + 1);
      setHistory([...trimmedHistory, nextRevision]);
      setHistoryIndex(trimmedHistory.length);
      onRevisionAdded("Draft revision transcribed by scribe.");
    },
    [activeDraft, history, historyIndex, onRevisionAdded, scribe]
  );

  const handleUpdateBody = useCallback(
    (text: string) => {
      const trimmedHistory = history.slice(0, historyIndex + 1);
      setHistory([...trimmedHistory, { ...activeDraft, paragraphs: [text] }]);
      setHistoryIndex(trimmedHistory.length);
    },
    [activeDraft, history, historyIndex]
  );

  const handleUndo = useCallback(() => {
    if (!canUndo) return;
    setHistoryIndex((previousIndex) => previousIndex - 1);
  }, [canUndo]);

  const handleRedo = useCallback(() => {
    if (!canRedo) return;
    setHistoryIndex((previousIndex) => previousIndex + 1);
  }, [canRedo]);

  return {
    activeDraft,
    revisionCount: history.length,
    isScribeWorking: scribe.isScribeWorking,
    canUndo,
    canRedo,
    handleScribeRewrite,
    handleUpdateBody,
    handleUndo,
    handleRedo,
  };
}

function useLetterToast() {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((message: string) => {
    setToastMessage(message);
    setTimeout(() => {
      setToastMessage(null);
    }, TOAST_DURATION_MS);
  }, []);

  return { toastMessage, showToast };
}

function useLetterDocket(
  scribeName: string,
  onClose?: () => void,
  onShowToast?: (message: string) => void,
  onDecline?: () => void
) {
  const [stage, setStage] = useState<LetterStage>("reading");
  const [mode, setMode] = useState<"direct_quill" | "scribe">("scribe");
  const [isShelfActive, setIsShelfActive] = useState(false);

  const handleSelectDocket = useCallback(
    (choice: DocketChoice) => {
      if (choice === "decline") {
        onDecline?.();
        return;
      }
      if (choice === "aside") {
        setIsShelfActive(true);
        onShowToast?.("Letter returned quietly to the desk tray.");
        onClose?.();
        return;
      }
      setMode(choice === "write" ? "direct_quill" : "scribe");
      setStage("drafting");
      const message =
        choice === "write"
          ? "Quill dipped in gallnut ink. Solar journal opened."
          : `Summoning ${scribeName} to transcribe instructions.`;
      onShowToast?.(message);
    },
    [onClose, onDecline, onShowToast, scribeName]
  );

  const handleResumeFromShelf = useCallback(() => {
    setIsShelfActive(false);
  }, []);

  const handleReturnToReading = useCallback(() => {
    setStage("reading");
  }, []);

  const resetShelf = useCallback(() => {
    setIsShelfActive(false);
  }, []);

  return {
    stage,
    mode,
    isShelfActive,
    handleSelectDocket,
    handleResumeFromShelf,
    handleReturnToReading,
    resetShelf,
  };
}

interface UseLetterSealParameters {
  sceneId: string;
  activeDraft: DraftRevision;
  revisionCount: number;
  onSeal?: LetterSealHandler;
  onClose?: () => void;
  onAfterSeal: () => void;
  onShowToast: (message: string) => void;
}

function findSealProblem(prose: string): string | null {
  if (!prose.trim()) return SEAL_EMPTY_MESSAGE;
  if (prose.length > LETTER_SEAL_MAX_CHARS) return SEAL_TOO_LONG_MESSAGE;
  return null;
}

function useLetterSeal(parameters: UseLetterSealParameters) {
  const { sceneId, activeDraft, revisionCount, onSeal, onClose } = parameters;
  const { onAfterSeal, onShowToast } = parameters;
  const [isSealing, setIsSealing] = useState(false);

  const completeSeal = useCallback(
    async (submission: LetterSealSubmission): Promise<void> => {
      const isSent = await onSeal?.(submission);
      setIsSealing(false);
      if (isSent === false) {
        onShowToast(SEAL_FAILED_MESSAGE);
        return;
      }
      onAfterSeal();
      onClose?.();
    },
    [onSeal, onClose, onAfterSeal, onShowToast]
  );

  const handleSealAndSend = useCallback(() => {
    if (isSealing) return;
    const finalProse = joinProse(activeDraft.paragraphs);
    const problem = findSealProblem(finalProse);
    if (problem) {
      onShowToast(problem);
      return;
    }
    setIsSealing(true);
    const submission: LetterSealSubmission = {
      sceneId,
      finalProse,
      instructionSummary: activeDraft.instruction,
      revisionCount,
    };
    setTimeout(() => {
      void completeSeal(submission);
    }, SEAL_DISPATCH_DELAY_MS);
  }, [activeDraft, completeSeal, isSealing, onShowToast, revisionCount, sceneId]);

  return { isSealing, handleSealAndSend };
}

function handleReadingStageKey(
  key: string,
  onSelectDocket: (choice: DocketChoice) => void
): void {
  if (key === "1") {
    onSelectDocket("write");
    return;
  }
  if (key === "2") {
    onSelectDocket("scribe");
    return;
  }
  if (key === "3" || key === "Escape") {
    onSelectDocket("aside");
    return;
  }
  if (key === "4") {
    onSelectDocket("decline");
  }
}

function handleDraftingStageKey(
  event: KeyboardEvent,
  onReturnToReading: () => void,
  onSealAndSend: () => void
): void {
  if (event.key === "Escape") {
    onReturnToReading();
    return;
  }
  const isSubmitCombo =
    event.key === "Enter" && (event.metaKey || event.ctrlKey);
  if (isSubmitCombo) {
    onSealAndSend();
  }
}

interface LetterKeyboardHandlers {
  stage: LetterStage;
  onSelectDocket: (choice: DocketChoice) => void;
  onReturnToReading: () => void;
  onSealAndSend: () => void;
}

function useLetterKeyboardListener(handlers: LetterKeyboardHandlers): void {
  const { stage, onSelectDocket, onReturnToReading, onSealAndSend } = handlers;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isInteractiveInputTarget(event.target)) {
        return;
      }
      if (stage === "reading") {
        handleReadingStageKey(event.key, onSelectDocket);
        return;
      }
      if (stage === "drafting") {
        handleDraftingStageKey(event, onReturnToReading, onSealAndSend);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [stage, onSelectDocket, onReturnToReading, onSealAndSend]);
}

export function useLetterScene(
  letterPackage: StrategyLetterPackage,
  onSeal?: LetterSealHandler,
  onClose?: () => void,
  requestScribeDraft?: ScribeDraftRequester,
  onDecline?: () => void
) {
  const [isMuted, setIsMuted] = useState(false);
  const { toastMessage, showToast } = useLetterToast();
  const docket = useLetterDocket(
    letterPackage.scribe.name,
    onClose,
    showToast,
    letterPackage.isDeclinable === false ? undefined : onDecline
  );
  const draft = useDraftHistory(
    letterPackage.initialDraft,
    showToast,
    requestScribeDraft
  );
  const seal = useLetterSeal({
    sceneId: letterPackage.sceneId,
    activeDraft: draft.activeDraft,
    revisionCount: draft.revisionCount,
    onSeal,
    onClose,
    onAfterSeal: docket.resetShelf,
    onShowToast: showToast,
  });

  useLetterKeyboardListener({
    stage: docket.stage,
    onSelectDocket: docket.handleSelectDocket,
    onReturnToReading: docket.handleReturnToReading,
    onSealAndSend: seal.handleSealAndSend,
  });

  const handleToggleMute = useCallback(() => {
    setIsMuted((isCurrentlyMuted) => !isCurrentlyMuted);
  }, []);

  return {
    stage: docket.stage,
    mode: docket.mode,
    activeDraft: draft.activeDraft,
    isShelfActive: docket.isShelfActive,
    isMuted,
    isSealing: seal.isSealing,
    isScribeWorking: draft.isScribeWorking,
    toastMessage,
    canUndo: draft.canUndo,
    canRedo: draft.canRedo,
    handleSelectDocket: docket.handleSelectDocket,
    handleScribeRewrite: draft.handleScribeRewrite,
    handleUndo: draft.handleUndo,
    handleRedo: draft.handleRedo,
    handleUpdateBody: draft.handleUpdateBody,
    handleSealAndSend: seal.handleSealAndSend,
    handleToggleMute,
    handleResumeFromShelf: docket.handleResumeFromShelf,
  };
}
