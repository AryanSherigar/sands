import { KeyboardEvent, useEffect, useRef, useState } from "react";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { usePlayStore } from "../../../stores/play.store";
import { useVoiceInput, VoiceInputStatus } from "../../../hooks/useVoiceInput";
import { useInputTakeover } from "../../../hooks/useInputTakeover";
import { useIntrusivePlaceholder } from "../../../hooks/useIntrusivePlaceholder";
import { ActionMode } from "../../../types/play.types";
import {
  TURN_ACTION_COUNTER_VISIBLE_RATIO,
  TURN_ACTION_MAX_CHARS,
} from "../../../constants/turnInput.constants";
import { EBookActionDrawerProps } from "./ebook.types";

type DrawerModeKey = Extract<ActionMode, "do" | "say"> | "continue";

interface ModeOption {
  key: DrawerModeKey;
  label: string;
  prefix: string;
  hint: string;
}

const MODES: ModeOption[] = [
  {
    key: "do",
    label: "Do",
    prefix: "I ",
    hint: "Perform a physical deed or travel",
  },
  {
    key: "say",
    label: "Say",
    prefix: 'I say: "',
    hint: "Speak dialogue or call out",
  },
  {
    key: "continue",
    label: "Continue",
    prefix: "",
    hint: "Let the narrator carry the scene forward",
  },
];

const getActiveModeKey = (
  isContinueSelected: boolean,
  storedMode: ActionMode,
): DrawerModeKey => {
  if (isContinueSelected) return "continue";
  return storedMode === "say" ? "say" : "do";
};

const getModeButtonClass = (isActive: boolean, isSepia: boolean): string => {
  if (!isActive) return "opacity-60 hover:opacity-100 hover:bg-surface-raised";
  return isSepia
    ? "bg-[#2c2217] text-[#faf4e8] font-bold shadow-xs"
    : "bg-primary text-primary-contrast font-bold shadow-xs";
};

const getMicButtonClass = (
  voiceStatus: VoiceInputStatus,
  isSepia: boolean,
): string => {
  if (voiceStatus === "recording") {
    return "bg-danger border-danger text-white animate-pulse";
  }
  return isSepia
    ? "border-[#d8c7a8] text-[#2c2217] hover:bg-[#2c2217]/10"
    : "border-border-strong text-content-muted hover:bg-surface-raised";
};

const getMicButtonLabel = (voiceStatus: VoiceInputStatus): string => {
  if (voiceStatus === "recording") return "⏹";
  if (voiceStatus === "transcribing") return "…";
  return "🎙";
};

export function EBookActionDrawer({
  onSubmit,
  onContinue,
  onRetry,
  canRetry,
  isNarrating,
  playthroughId,
  actionChips = [],
}: EBookActionDrawerProps) {
  const [text, setText] = useState("");
  const [focusCount, setFocusCount] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isContinueSelected, setIsContinueSelected] = useState(false);
  const storedMode = usePlayStore((s) => s.active_mode);
  const setActiveMode = usePlayStore((s) => s.setActiveMode);
  const focusRequested = usePlayStore((s) => s.is_action_drawer_open);
  const closeActionDrawer = usePlayStore((s) => s.closeActionDrawer);
  const theme = usePlayStore((s) => s.ebook_theme);
  const isSepia = theme === "antique-sepia";
  const isAlphaMode = useIsAlphaMode();

  const activeKey = getActiveModeKey(isContinueSelected, storedMode);
  const currentMode = MODES.find((m) => m.key === activeKey) ?? MODES[0];
  const standardPlaceholder = isContinueSelected
    ? `${currentMode.hint}...`
    : `Action (${currentMode.label}): ${currentMode.hint.toLowerCase()}...`;
  const { placeholder, isIntrusive } = useIntrusivePlaceholder(
    standardPlaceholder,
    text.length > 0,
    focusCount,
  );
  const { takeoverText, isLocked } = useInputTakeover();
  const isTakenOver = takeoverText !== null;
  const isEerie = isIntrusive || isTakenOver;

  const characterCount = Array.from(text).length;
  const isCounterVisible =
    characterCount >= TURN_ACTION_MAX_CHARS * TURN_ACTION_COUNTER_VISIBLE_RATIO;
  const isOverLimit = characterCount > TURN_ACTION_MAX_CHARS;

  const handleTranscribed = (transcript: string) => {
    setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
  };
  const {
    status: voiceStatus,
    isSupported: isVoiceSupported,
    errorMessage: voiceErrorMessage,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceInput(handleTranscribed, playthroughId);

  const handleMicClick = () => {
    if (voiceStatus === "recording") {
      void stopRecording();
    } else if (voiceStatus === "idle" || voiceStatus === "error") {
      void startRecording();
    }
  };

  useEffect(() => {
    if (!focusRequested) return;
    setIsContinueSelected(false);
    setTimeout(() => textareaRef.current?.focus(), 100);
    closeActionDrawer();
  }, [focusRequested, closeActionDrawer]);

  const handleModeSelect = (key: DrawerModeKey): void => {
    setIsContinueSelected(key === "continue");
    if (key !== "continue") setActiveMode(key);
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSubmit = () => {
    if (isNarrating || isLocked) return;
    if (isContinueSelected) {
      cancelRecording();
      setIsContinueSelected(false);
      onContinue();
      return;
    }
    if (!text.trim()) return;
    onSubmit(text.trim());
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleChipClick = (chipText: string): void => {
    if (isLocked) return;
    setText(chipText);
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const drawerStyle = isSepia
    ? "bg-[#f5ebd7] border-[#d8c7a8] text-[#2c2217] shadow-modal"
    : "bg-surface-sunken border-border-subtle text-content shadow-modal";

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 p-3 sm:p-4 flex justify-center">
      <div
        className={`w-full max-w-2xl p-4 sm:p-5 rounded-2xl border backdrop-blur-xl flex flex-col gap-3 ${drawerStyle}`}
      >
        <div className="flex items-center justify-between border-b border-inherit/20 pb-3">
          <div className="flex items-center gap-1 sm:gap-1.5 font-mono text-xs">
            {MODES.map((mode) => {
              const isActive = activeKey === mode.key;
              return (
                <button
                  key={mode.key}
                  type="button"
                  onClick={() => handleModeSelect(mode.key)}
                  title={mode.hint}
                  className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${getModeButtonClass(
                    isActive,
                    isSepia,
                  )}`}
                >
                  {mode.label}
                </button>
              );
            })}
          </div>

          {canRetry && !isNarrating && (
            <button
              type="button"
              onClick={onRetry}
              className="p-1 rounded opacity-75 hover:opacity-100 transition-opacity cursor-pointer font-mono text-xs"
              title="Retry Narrator Turn"
            >
              ↺ Retry
            </button>
          )}
        </div>

        {actionChips.length > 0 && !isContinueSelected && (
          <div className="flex flex-wrap gap-1.5 sm:gap-2">
            {actionChips.map((chip, index) => (
              <button
                key={`${chip}-${index}`}
                type="button"
                onClick={() => handleChipClick(chip)}
                disabled={isNarrating}
                className={`px-3 py-1 rounded-full border font-mono text-[11px] transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                  isSepia
                    ? "border-[#d8c7a8] text-[#2c2217] hover:bg-[#2c2217]/10"
                    : "border-border-strong text-content-muted hover:bg-surface-raised"
                }`}
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={isLocked || isContinueSelected ? "" : text}
            maxLength={TURN_ACTION_MAX_CHARS}
            disabled={isNarrating || isLocked || isContinueSelected}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setFocusCount((count) => count + 1)}
            aria-label={standardPlaceholder}
            placeholder={takeoverText ?? placeholder}
            className={`flex-1 bg-transparent border border-inherit/30 rounded-xl p-3 text-sm md:text-base font-serif focus:outline-hidden focus:border-primary resize-none leading-relaxed ${
              isEerie ? "placeholder:font-eerie placeholder:text-red-400/60" : ""
            }`}
          />

          {isVoiceSupported && !isAlphaMode && !isContinueSelected && (
            <button
              type="button"
              disabled={isNarrating || voiceStatus === "transcribing"}
              onClick={handleMicClick}
              title={voiceStatus === "recording" ? "Stop recording" : "Speak your action"}
              className={`px-4 py-3 rounded-xl font-mono text-xs font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0 border ${getMicButtonClass(
                voiceStatus,
                isSepia,
              )}`}
            >
              {getMicButtonLabel(voiceStatus)}
            </button>
          )}

          <button
            type="button"
            disabled={(!isContinueSelected && !text.trim()) || isNarrating || isLocked}
            onClick={handleSubmit}
            className={`px-5 py-3 rounded-xl font-mono text-xs font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0 ${
              isSepia
                ? "bg-[#2c2217] hover:bg-[#433523] text-[#faf4e8]"
                : "bg-primary hover:bg-content text-primary-contrast"
            }`}
          >
            Submit ↵
          </button>
        </div>

        <div className="flex items-center justify-between text-[11px] font-mono opacity-60 px-1">
          <span>
            {voiceErrorMessage ??
              (isContinueSelected ? null : (
              <>
                Prefix:{" "}
                <em className="not-italic font-semibold">{currentMode.prefix}</em>
              </>
              ))}
          </span>
          {isCounterVisible && (
            <span
              aria-live="polite"
              className={isOverLimit ? "text-danger font-bold" : ""}
            >
              {characterCount}/{TURN_ACTION_MAX_CHARS}
              {isOverLimit && " - extra text will be cut"}
            </span>
          )}
          <span>Press Cmd/Ctrl + Enter to send</span>
        </div>
      </div>
    </div>
  );
}
