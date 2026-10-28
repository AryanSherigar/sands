import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { PLAYTEST_ACTION_PLACEHOLDER } from "../../constants/playtest";
import type { PlaytestActionBoxProps } from "./PlaytestTab.types";

export const PlaytestActionBox: React.FC<PlaytestActionBoxProps> = ({ isDisabled, onSubmit }) => {
  const [text, setText] = useState("");
  const canSend = !isDisabled && text.trim().length > 0;

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (!canSend) return;
    onSubmit(text.trim());
    setText("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-border-subtle p-3">
      <textarea
        aria-label={PLAYTEST_ACTION_PLACEHOLDER}
        placeholder={PLAYTEST_ACTION_PLACEHOLDER}
        value={text}
        rows={2}
        disabled={isDisabled}
        onChange={(event) => setText(event.target.value)}
        className="min-w-0 flex-1 resize-none rounded-sm border border-border-strong bg-surface-inset px-2 py-1.5 text-body text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden disabled:opacity-60"
      />
      <Button type="submit" disabled={!canSend}>
        Send
      </Button>
    </form>
  );
};
