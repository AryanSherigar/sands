import React from "react";
import { panelForIssue } from "../../lib/strategyPanels";
import type { StrategyIssueListProps } from "./StrategyWorkspace.types";

export const StrategyIssueList: React.FC<StrategyIssueListProps> = ({ issues, tone, onOpenPanel }) => (
  <ul className={`list-disc space-y-1 pl-5 text-sm ${tone}`}>
    {issues.map((issue) => {
      const panel = panelForIssue(issue);
      return (
        <li key={`${issue.code}:${issue.path}:${issue.message}`}>
          {panel ? (
            <button type="button" className="text-left underline" onClick={() => onOpenPanel(panel)}>
              {issue.message}
            </button>
          ) : (
            issue.message
          )}
        </li>
      );
    })}
  </ul>
);
