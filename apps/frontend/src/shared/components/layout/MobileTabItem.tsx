import React from "react";
import { Link } from "react-router-dom";
import { cn } from "@/shared/lib/cn";
import type { MobileTabItemProps } from "./MobileTabItem.types";

export const MobileTabItem: React.FC<MobileTabItemProps> = ({
  label,
  Icon,
  isActive,
  to,
  onSelect,
}) => {
  const className = cn(
    "flex flex-1 flex-col items-center justify-center gap-1 font-sans text-xs focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent",
    isActive ? "text-content" : "text-content-muted",
  );
  const content = (
    <>
      <Icon size={22} />
      {label}
    </>
  );

  if (onSelect) {
    return (
      <button type="button" onClick={onSelect} className={className}>
        {content}
      </button>
    );
  }
  return (
    <Link
      to={to ?? "/"}
      aria-current={isActive ? "page" : undefined}
      className={className}
    >
      {content}
    </Link>
  );
};
