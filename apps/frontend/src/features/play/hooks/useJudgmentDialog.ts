import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_JUDGMENT_VERDICT,
  JUDGMENT_VERDICTS,
} from "../constants/judgment.constants";
import type {
  JudgmentNuanceId,
  JudgmentPronouncement,
  JudgmentVerdictId,
} from "../types/judgmentScene.types";

interface UseJudgmentDialogOptions {
  isActive: boolean;
  isBusy: boolean;
  spokenExchangesRemaining: number;
  onSpeak: (text: string) => Promise<boolean>;
  onPronounce: (pronouncement: JudgmentPronouncement) => Promise<boolean>;
  onClose: () => void;
}

const isTypingTarget = (target: EventTarget | null): boolean =>
  target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;

export function useJudgmentDialog(options: UseJudgmentDialogOptions) {
  const { isActive, isBusy, spokenExchangesRemaining, onSpeak, onPronounce, onClose } = options;
  const [selectedVerdict, setSelectedVerdict] = useState<JudgmentVerdictId>(
    DEFAULT_JUDGMENT_VERDICT,
  );
  const [selectedNuance, setSelectedNuance] = useState<JudgmentNuanceId | null>(null);
  const [draftText, setDraftText] = useState("");
  const [isConfirmingExit, setIsConfirmingExit] = useState(false);

  const handleSelectVerdict = useCallback((verdict: JudgmentVerdictId): void => {
    setSelectedVerdict(verdict);
    setSelectedNuance(null);
  }, []);

  const handleSelectNuance = useCallback((nuance: JudgmentNuanceId): void => {
    setSelectedNuance((current) => (current === nuance ? null : nuance));
  }, []);

  const handleSpeak = useCallback((): void => {
    const text = draftText.trim();
    if (!text || isBusy || spokenExchangesRemaining <= 0) return;
    setDraftText("");
    void onSpeak(text).then((isSent) => {
      if (!isSent) setDraftText(text);
    });
  }, [draftText, isBusy, spokenExchangesRemaining, onSpeak]);

  const handlePronounce = useCallback((): void => {
    if (isBusy) return;
    void onPronounce({
      verdict: selectedVerdict,
      nuance: selectedNuance,
      decreeText: draftText.trim(),
    });
  }, [isBusy, onPronounce, selectedVerdict, selectedNuance, draftText]);

  const handleRequestExit = useCallback((): void => setIsConfirmingExit(true), []);
  const handleStay = useCallback((): void => setIsConfirmingExit(false), []);
  const handleLeave = useCallback((): void => {
    setIsConfirmingExit(false);
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!isActive) return undefined;
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setIsConfirmingExit(true);
        return;
      }
      const verdict = JUDGMENT_VERDICTS.find((item) => item.shortcut === event.key);
      if (verdict && !isTypingTarget(event.target) && !isBusy) handleSelectVerdict(verdict.id);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isActive, isBusy, handleSelectVerdict]);

  return {
    selectedVerdict,
    selectedNuance,
    draftText,
    isConfirmingExit,
    handleSelectVerdict,
    handleSelectNuance,
    handleDraftChange: setDraftText,
    handleSpeak,
    handlePronounce,
    handleRequestExit,
    handleStay,
    handleLeave,
  };
}
