import type React from "react";

export interface TerminalPromptProps {
  input: string;
  onChange: (value: string) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void;
}
