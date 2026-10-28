import React from "react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { HAND_LABELS } from "../../constants/sheetRule";
import { SheetRuleRowProps } from "./SheetRuleRow.types";

export const SheetRuleRow: React.FC<SheetRuleRowProps> = ({
  rule,
  index,
  total,
  onEdit,
  onDelete,
  onMove,
}) => (
  <li
    data-testid={`sheet-rule-row-${rule.rule_id}`}
    className="rounded-md flex items-center gap-3 border border-border-subtle bg-surface-inset px-3 py-2"
  >
    <Badge>{rule.number}</Badge>
    <div className="min-w-0 flex-1">
      <p className="truncate text-sm text-content">{rule.text}</p>
      <p className="truncate text-xs text-content-faint">
        {rule.key} · {HAND_LABELS[rule.source_style]}
        {rule.is_ai_flaggable ? " · narrator may flag" : ""}
      </p>
    </div>
    <Button
      variant="secondary"
      size="sm"
      disabled={index === 0}
      onClick={() => onMove(index, -1)}
      aria-label={`Move rule ${rule.number} up`}
    >
      ↑
    </Button>
    <Button
      variant="secondary"
      size="sm"
      disabled={index === total - 1}
      onClick={() => onMove(index, 1)}
      aria-label={`Move rule ${rule.number} down`}
    >
      ↓
    </Button>
    <Button variant="secondary" size="sm" onClick={() => onEdit(rule)}>
      Edit
    </Button>
    <Button variant="danger" size="sm" onClick={() => onDelete(rule.rule_id)}>
      Delete
    </Button>
  </li>
);
