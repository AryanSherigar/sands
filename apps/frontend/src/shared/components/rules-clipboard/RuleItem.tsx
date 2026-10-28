import React from "react";
import { RuleItemProps } from "./RuleItem.types";

const STATUS_LABELS: Record<RuleItemProps["rule"]["status"], string> = {
  intact: "intact",
  active_threat: "under threat",
  violated: "violated",
  corrupted: "corrupted",
};

export const RuleItem: React.FC<RuleItemProps> = ({ rule }) => (
  <li
    data-status={rule.status}
    className={`rule-item rule-status-${rule.status} rule-hand-${rule.source_style}`}
  >
    <span className="rule-number" aria-hidden="true">
      {rule.number}.
    </span>
    <span className="rule-text">{rule.text}</span>
    <span className="sr-only">{`Rule ${rule.number}, ${STATUS_LABELS[rule.status]}`}</span>
  </li>
);
