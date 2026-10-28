import React from "react";
import { motion } from "motion/react";
import { cn } from "@/shared/lib/cn";
import { useAppSidebar } from "./appSidebarContext";

export interface SidebarButtonProps {
  icon: React.ReactNode;
  label: string;
  isActive?: boolean;
  trailing?: React.ReactNode;
  onClick: () => void;
}

export const SidebarButton: React.FC<SidebarButtonProps> = ({
  icon,
  label,
  isActive = false,
  trailing,
  onClick,
}) => {
  const { collapsed } = useAppSidebar();

  return (
    <button
      type="button"
      onClick={onClick}
      title={collapsed ? label : undefined}
      className={cn(
        "group/row relative flex w-full items-center gap-3 rounded-lg py-2 text-left font-sans text-sm transition-colors",
        collapsed ? "justify-center px-0" : "px-2.5",
        isActive
          ? "bg-surface-overlay text-content"
          : "text-content-muted hover:bg-surface-raised/70 hover:text-content",
      )}
    >
      {isActive && !collapsed && (
        <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
      )}
      <span className="flex h-5 w-5 shrink-0 items-center justify-center">
        {icon}
      </span>
      <motion.span
        animate={{ opacity: collapsed ? 0 : 1, width: collapsed ? 0 : "auto" }}
        className="overflow-hidden whitespace-nowrap"
      >
        {label}
      </motion.span>
      {trailing && !collapsed && (
        <span className="ml-auto text-micro text-content-faint">{trailing}</span>
      )}
    </button>
  );
};
