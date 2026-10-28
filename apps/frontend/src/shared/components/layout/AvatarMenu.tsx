import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  IconChartBar,
  IconLogout,
  IconPencil,
  IconSettings,
  IconUser,
} from "@tabler/icons-react";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { getInitial } from "./getInitial";
import type { AvatarMenuProps } from "./AvatarMenu.types";

const MENU_ITEMS = [
  { to: "/profile", label: "View profile", Icon: IconUser, isCreatorOnly: false },
  {
    to: "/profile?tab=creations",
    label: "My scenarios",
    Icon: IconPencil,
    isCreatorOnly: true,
  },
  {
    to: "/studio/stats",
    label: "Creator stats",
    Icon: IconChartBar,
    isCreatorOnly: true,
  },
  { to: "/settings", label: "Settings", Icon: IconSettings, isCreatorOnly: false },
];

const ARROW_STEPS: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };

const ITEM_CLASSES =
  "flex w-full items-center gap-2.5 px-4 py-2 text-left transition-colors hover:bg-surface-raised hover:text-content focus-visible:bg-surface-raised focus-visible:outline-hidden";

export const AvatarMenu: React.FC<AvatarMenuProps> = ({ user, onSignOut }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isAlphaMode = useIsAlphaMode();
  const menuItems = MENU_ITEMS.filter(
    (item) => !(isAlphaMode && item.isCreatorOnly),
  );
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    menuRef.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    const handlePointerDown = (event: MouseEvent): void => {
      if (!rootRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [isOpen]);

  const handleMenuKeyDown = (event: React.KeyboardEvent): void => {
    if (event.key === "Escape") {
      setIsOpen(false);
      triggerRef.current?.focus();
      return;
    }
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? [],
    );
    const step = ARROW_STEPS[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const index = items.indexOf(document.activeElement as HTMLElement);
    items[(index + step + items.length) % items.length]?.focus();
  };

  const handleTriggerKeyDown = (event: React.KeyboardEvent): void => {
    if (event.key !== "ArrowDown") return;
    event.preventDefault();
    setIsOpen(true);
  };

  const handleSignOut = (): void => {
    setIsOpen(false);
    onSignOut();
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label="Account menu"
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleTriggerKeyDown}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-overlay font-sans text-sm font-medium text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        {getInitial(user.display_name)}
      </button>
      {isOpen && (
        <div
          ref={menuRef}
          role="menu"
          onKeyDown={handleMenuKeyDown}
          className="absolute right-0 z-50 mt-2 w-56 origin-top-right animate-in fade-in zoom-in-98 overflow-hidden rounded-lg border border-border-subtle bg-surface-overlay py-1 font-sans text-sm text-content-muted shadow-elevated duration-150"
        >
          <p className="truncate px-4 py-2 font-medium text-content">
            {user.display_name}
          </p>
          {menuItems.map(({ to, label, Icon }) => (
            <Link
              key={to}
              to={to}
              role="menuitem"
              onClick={() => setIsOpen(false)}
              className={ITEM_CLASSES}
            >
              <Icon size={16} className="text-content-faint" />
              {label}
            </Link>
          ))}
          <div role="separator" className="my-1 h-px bg-border-subtle" />
          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            className={`${ITEM_CLASSES} text-danger hover:bg-danger/10`}
          >
            <IconLogout size={16} />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
};
