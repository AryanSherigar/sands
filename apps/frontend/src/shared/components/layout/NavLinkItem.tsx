import React from "react";
import { Link } from "react-router-dom";
import { cn } from "@/shared/lib/cn";
import type { NavLinkItemProps } from "./NavLinkItem.types";

export const NavLinkItem: React.FC<NavLinkItemProps> = ({
  to,
  label,
  isActive,
}) => (
  <Link
    to={to}
    aria-current={isActive ? "page" : undefined}
    className={cn(
      "flex h-full items-center px-1 font-sans text-sm transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent",
      isActive
        ? "font-bold text-primary"
        : "font-medium text-content-muted hover:text-content",
    )}
  >
    {label}
  </Link>
);
