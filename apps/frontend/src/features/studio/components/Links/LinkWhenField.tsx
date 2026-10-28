import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { LINK_WHEN_LABEL } from "../../constants/cardValues";
import { useOpenFullEditor } from "../../hooks/useOpenFullEditor";
import type { SentenceOutput } from "../../lib/sentenceRows";
import { isFieldExpression } from "../../lib/fieldExpression";
import { AdvancedLogicNotice } from "../SentenceBuilder/AdvancedLogicNotice";
import { SentenceBuilder } from "../SentenceBuilder/SentenceBuilder";
import type { LinkWhenFieldProps } from "./Links.types";

export const LinkWhenField: React.FC<LinkWhenFieldProps> = ({ whenActive, onChange }) => {
  const openFullEditor = useOpenFullEditor();
  const [isOpen, setIsOpen] = useState(whenActive !== null);
  const isStoredPresent = whenActive !== null && Object.keys(whenActive).length > 0;
  const expression = whenActive !== null && isFieldExpression(whenActive) ? whenActive : null;

  const handleChange = (next: SentenceOutput | null): void =>
    onChange(next ? { ...next.expression } : null);

  if (!isOpen) {
    return (
      <Button type="button" variant="ghost" size="sm" onClick={() => setIsOpen(true)}>
        + {LINK_WHEN_LABEL}
      </Button>
    );
  }

  if (isStoredPresent && expression === null) {
    return <AdvancedLogicNotice onOpenFullEditor={openFullEditor} />;
  }

  return (
    <div className="w-full space-y-2">
      <p className="text-meta font-medium text-content-muted">{LINK_WHEN_LABEL}</p>
      <SentenceBuilder
        value={expression}
        onChange={handleChange}
        onOpenFullEditor={openFullEditor}
      />
    </div>
  );
};
