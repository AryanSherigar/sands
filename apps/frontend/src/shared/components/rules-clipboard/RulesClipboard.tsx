import React from "react";
import { RuleItem } from "./RuleItem";
import { RulesClipboardProps } from "./RulesClipboard.types";

const TALLY_GROUP_SIZE = 5;

const tallyMarks = (count: number): string => {
  const groups = Math.floor(count / TALLY_GROUP_SIZE);
  const rest = count % TALLY_GROUP_SIZE;
  return [
    ...Array<string>(groups).fill("卅"),
    ...Array<string>(rest).fill("|"),
  ].join(" ");
};

export const RulesClipboard: React.FC<RulesClipboardProps> = ({
  rules,
  duties = [],
  isMotionReduced,
}) => {
  const violatedCount = rules.filter((rule) => rule.status === "violated").length;

  return (
    <aside
      aria-label="Rules clipboard"
      data-motion={isMotionReduced ? "reduced" : "full"}
      className="rules-clipboard"
    >
      {duties.length > 0 && (
        <>
          <h2 className="rules-clipboard-title">Duties</h2>
          <ul aria-label="Duties" className="rules-list">
            {duties.map((duty) => (
              <li key={duty} className="rule-item rule-hand-typed">
                {duty}
              </li>
            ))}
          </ul>
        </>
      )}
      <h2 className="rules-clipboard-title">Rules</h2>
      <ol aria-live="polite" aria-relevant="additions" className="rules-list">
        {rules.map((rule) => (
          <RuleItem key={rule.key} rule={rule} />
        ))}
      </ol>
      {violatedCount > 0 && (
        <p className="rules-tally">
          <span className="sr-only">{`Rules broken: ${violatedCount}`}</span>
          <span aria-hidden="true">{tallyMarks(violatedCount)}</span>
        </p>
      )}
    </aside>
  );
};
