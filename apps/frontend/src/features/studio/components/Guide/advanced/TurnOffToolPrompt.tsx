import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { TurnOffToolPromptProps } from "./Advanced.types";

export const TurnOffToolPrompt: React.FC<TurnOffToolPromptProps> = ({ tool }) => {
  if (!tool.shouldOffer) return null;

  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border-subtle bg-surface-inset p-3"
    >
      <p className="text-meta text-content">{tool.question}</p>
      <div className="flex gap-2">
        <Button type="button" size="sm" variant="ghost" onClick={tool.dismiss}>
          Not now
        </Button>
        <Button type="button" size="sm" variant="secondary" onClick={() => void tool.confirm()}>
          Turn off
        </Button>
      </div>
    </div>
  );
};
