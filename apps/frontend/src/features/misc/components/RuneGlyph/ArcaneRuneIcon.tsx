import React from "react";
import type { ArcaneRuneIconProps } from "./ArcaneRuneIcon.types";

export const ArcaneRuneIcon: React.FC<ArcaneRuneIconProps> = ({
  className = "h-6 w-6 text-accent transition-transform duration-700 group-hover:rotate-45",
}) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="9" className="opacity-40" />
      <polygon points="12 3 20 18 4 18" className="opacity-70" />
      <circle cx="12" cy="13" r="2" fill="currentColor" />
      <line x1="12" y1="3" x2="12" y2="7" />
      <line x1="4" y1="18" x2="8" y2="15" />
      <line x1="20" y1="18" x2="16" y2="15" />
    </svg>
  );
};
