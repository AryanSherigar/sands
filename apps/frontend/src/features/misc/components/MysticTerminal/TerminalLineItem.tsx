import React from "react";
import type { TerminalLineItemProps } from "./TerminalLineItem.types";
import { TerminalFactCard } from "./TerminalFactCard";

export const TerminalLineItem: React.FC<TerminalLineItemProps> = ({ line }) => {
  if (line.fact) {
    return <TerminalFactCard fact={line.fact} />;
  }

  if (line.type === "input") {
    return (
      <div className="font-mono text-xs text-accent">
        <span className="text-content-faint mr-1.5">{">"}</span>
        {line.content}
      </div>
    );
  }

  if (line.type === "error") {
    return (
      <div className="font-mono text-xs text-danger">
        {line.content}
      </div>
    );
  }

  return (
    <div className="whitespace-pre-wrap font-mono text-xs text-content-muted leading-relaxed">
      {line.content}
    </div>
  );
};
