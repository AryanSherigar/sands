import React from "react";
import { TierPipsProps } from "./TierPips.types";

export const TierPips: React.FC<TierPipsProps> = ({ label, options, value }) => (
  <div
    role="group"
    aria-label={`${label} ${value}`}
    className="flex items-center gap-2 font-mono text-xs"
  >
    <span className="opacity-60">{label}</span>
    <ol className="flex items-center gap-1 list-none p-0 m-0">
      {options.map((option) => (
        <li
          key={option}
          data-active={option === value}
          className="tier-pip h-2 w-2 rounded-full border border-current"
        >
          <span className="sr-only">{option}</span>
        </li>
      ))}
    </ol>
    <span className="font-semibold">{value}</span>
  </div>
);
