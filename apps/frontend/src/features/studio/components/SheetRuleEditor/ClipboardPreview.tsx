import React, { useState } from "react";
import { RulesClipboard } from "@/shared/components/rules-clipboard/RulesClipboard";
import { Select } from "@/shared/components/ui/Select";
import type { RuleSheetItem, RuleStatus } from "@/shared/types/rule-sheet.types";
import { STATUS_LABELS } from "../../constants/sheetRule";
import { ClipboardPreviewProps } from "./ClipboardPreview.types";

const STATUS_CHOICES = (
  ["intact", "active_threat", "violated", "corrupted"] as const
).map((status) => ({ value: status, label: STATUS_LABELS[status] }));

export const ClipboardPreview: React.FC<ClipboardPreviewProps> = ({ rules }) => {
  const [overrides, setOverrides] = useState<Record<string, RuleStatus>>({});
  const items: RuleSheetItem[] = rules.map((rule) => ({
    key: rule.key,
    number: rule.number,
    text: rule.text,
    status: overrides[rule.key] ?? "intact",
    source_style: rule.source_style,
  }));

  return (
    <section aria-label="Clipboard preview" className="space-y-2">
      <h2 className="text-sm font-semibold text-content">Clipboard preview</h2>
      <div className="grid grid-cols-2 gap-2">
        {rules.map((rule) => (
          <Select
            key={rule.key}
            aria-label={`Preview status of rule ${rule.number}`}
            options={STATUS_CHOICES}
            value={overrides[rule.key] ?? "intact"}
            onChange={(event) =>
              setOverrides({
                ...overrides,
                [rule.key]: event.target.value as RuleStatus,
              })
            }
          />
        ))}
      </div>
      <RulesClipboard rules={items} isMotionReduced />
    </section>
  );
};
