import { useState } from "react";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import {
  FLAG_NOTE_MAX_CHARS,
  FLAG_REASONS,
  LOCAL_TURN_ID_PREFIX,
} from "../../../constants/alpha-feedback.constants";
import { useFlagNarration } from "../../../hooks/useFlagNarration";
import type { FlagReason } from "../../../types/alphaFeedback.types";
import type { NarrationFlagProps } from "./NarrationFlag.types";

const BUTTON_CLASSES =
  "min-h-11 px-3 rounded-lg border border-inherit/20 font-mono text-xs hover:bg-surface-raised cursor-pointer transition-colors disabled:opacity-50";

export function NarrationFlag({ turnId }: NarrationFlagProps) {
  const isAlphaMode = useIsAlphaMode();
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [reasons, setReasons] = useState<FlagReason[]>([]);
  const [note, setNote] = useState("");
  const [isSent, setIsSent] = useState(false);
  const { mutate, isPending, isError } = useFlagNarration();

  const isSaved = !turnId.startsWith(LOCAL_TURN_ID_PREFIX);
  if (!isAlphaMode || !isSaved) return null;

  const send = (chosen: FlagReason[], text?: string): void => {
    mutate(
      { turnId, request: { reasons: chosen, ...(text && { note: text }) } },
      {
        onSuccess: () => {
          setIsSent(true);
          setIsDetailOpen(false);
        },
      },
    );
  };

  const handleToggleReason = (reason: FlagReason): void => {
    setReasons((current) =>
      current.includes(reason)
        ? current.filter((item) => item !== reason)
        : [...current, reason],
    );
  };

  if (isSent) {
    return <p className="font-mono text-xs opacity-70">Flagged. Thank you.</p>;
  }

  return (
    <div className="my-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={isPending}
          onClick={() => send(["broke_rule"])}
          className={BUTTON_CLASSES}
        >
          This broke a rule
        </button>
        <button
          type="button"
          aria-expanded={isDetailOpen}
          onClick={() => setIsDetailOpen((isOpen) => !isOpen)}
          className={BUTTON_CLASSES}
        >
          Something else
        </button>
      </div>
      {isError && <p className="font-mono text-xs text-danger">Could not send the flag.</p>}
      {isDetailOpen && (
        <div className="space-y-3 rounded-lg border border-border-strong bg-surface-overlay p-3 shadow-float">
          <div className="flex flex-wrap gap-3">
            {FLAG_REASONS.map((option) => (
              <label key={option.value} className="flex min-h-11 items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={reasons.includes(option.value)}
                  onChange={() => handleToggleReason(option.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
          <textarea
            aria-label="Note"
            value={note}
            maxLength={FLAG_NOTE_MAX_CHARS}
            onChange={(event) => setNote(event.target.value)}
            className="min-h-16 w-full rounded-md border border-border-strong bg-surface-raised p-2 text-xs text-content"
          />
          <button
            type="button"
            disabled={isPending || reasons.length === 0}
            onClick={() => send(reasons, note.trim())}
            className={BUTTON_CLASSES}
          >
            Send flag
          </button>
        </div>
      )}
    </div>
  );
}
