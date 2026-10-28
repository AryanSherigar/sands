import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { SCENE_MESSAGE_MAX_CHARS } from "../../../constants/scene.constants";
import type { SceneComposerProps } from "./SceneComposer.types";

export const SceneComposer: React.FC<SceneComposerProps> = ({
  isDisabled,
  exchangesRemaining,
  onSend,
}) => {
  const [text, setText] = useState("");
  const trimmed = text.trim();
  const canSend = !isDisabled && trimmed.length > 0;

  const handleSend = (): void => {
    if (!canSend) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    handleSend();
  };

  return (
    <div className="flex flex-col gap-2 border-t border-border-subtle pt-3">
      <textarea
        aria-label="Your words"
        value={text}
        maxLength={SCENE_MESSAGE_MAX_CHARS}
        disabled={isDisabled}
        rows={2}
        placeholder="Speak to the ruler…"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        className="w-full resize-none rounded-md border border-border-strong bg-surface-raised px-3 py-2 text-sm text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-40"
      />
      <div className="flex items-center justify-between">
        <span className="text-micro text-content-muted">
          {exchangesRemaining} {exchangesRemaining === 1 ? "exchange" : "exchanges"} left
        </span>
        <Button size="sm" disabled={!canSend} onClick={handleSend}>
          Speak
        </Button>
      </div>
    </div>
  );
};
