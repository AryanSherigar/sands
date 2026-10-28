import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { ADVANCED_LOGIC_MESSAGE, OPEN_FULL_EDITOR_LABEL } from "../../constants/sentenceBuilder";
import type { AdvancedLogicNoticeProps } from "./SentenceBuilder.types";

export const AdvancedLogicNotice: React.FC<AdvancedLogicNoticeProps> = ({ onOpenFullEditor }) => (
  <div
    role="note"
    className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border-subtle bg-surface-inset p-3"
  >
    <p className="text-meta text-content-muted">{ADVANCED_LOGIC_MESSAGE}</p>
    {onOpenFullEditor && (
      <Button type="button" variant="secondary" size="sm" onClick={onOpenFullEditor}>
        {OPEN_FULL_EDITOR_LABEL}
      </Button>
    )}
  </div>
);
