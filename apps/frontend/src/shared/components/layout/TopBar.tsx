import React from "react";
import { getPrimaryNavLinks } from "@/shared/constants/navigation";
import { cn } from "@/shared/lib/cn";
import { useLocation } from "react-router-dom";
import { AccountSlot } from "./AccountSlot";
import { NavLinkItem } from "./NavLinkItem";
import { SearchField } from "./SearchField";
import { ThemeToggle } from "./ThemeToggle";
import { Wordmark } from "./Wordmark";
import { isNavLinkActive } from "./isNavLinkActive";
import type { TopBarProps } from "./TopBar.types";

export const TopBar: React.FC<TopBarProps> = ({
  isTransparent,
  isCondensed,
}) => {
  const { pathname } = useLocation();

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full transition-[background-color,border-color,height] duration-150",
        isCondensed ? "h-14" : "h-16",
        isTransparent
          ? "border-b border-transparent bg-transparent"
          : "border-b border-border-subtle bg-surface/90 backdrop-blur-md",
      )}
    >
      <div className="mx-auto flex h-full max-w-[1440px] items-center gap-8 px-6">
        <Wordmark />
        <nav aria-label="Primary" className="flex h-full items-center gap-6">
          {getPrimaryNavLinks().map((link) => (
            <NavLinkItem
              key={link.to}
              to={link.to}
              label={link.label}
              isActive={isNavLinkActive(link, pathname)}
            />
          ))}
        </nav>
        <SearchField className="ml-auto w-full min-w-[320px] max-w-[480px]" />
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <AccountSlot />
        </div>
      </div>
    </header>
  );
};
