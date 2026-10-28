import React, { useEffect } from "react";
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
  IconX,
} from "@tabler/icons-react";

type ToastType = "error" | "danger" | "success" | "warning" | "info";

export interface ToastProps {
  message: string;
  type?: ToastType;
  onClose: () => void;
  durationMs?: number;
}

interface TypeConfig {
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
  colorClass: string;
}

const TYPE_CONFIG: Record<ToastType, TypeConfig> = {
  error: {
    icon: IconAlertCircle,
    colorClass: "text-danger",
  },
  danger: {
    icon: IconAlertCircle,
    colorClass: "text-danger",
  },
  success: {
    icon: IconCircleCheck,
    colorClass: "text-success",
  },
  warning: {
    icon: IconAlertTriangle,
    colorClass: "text-warning",
  },
  info: {
    icon: IconInfoCircle,
    colorClass: "text-info",
  },
};

export const Toast: React.FC<ToastProps> = ({
  message,
  type = "info",
  onClose,
  durationMs = 5000,
}) => {
  useEffect(() => {
    const timer = setTimeout(onClose, durationMs);
    return () => clearTimeout(timer);
  }, [onClose, durationMs]);

  const { icon: Icon, colorClass } = TYPE_CONFIG[type] ?? TYPE_CONFIG.info;

  return (
    <div
      role="status"
      className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-md border border-border-strong bg-surface-overlay px-4 py-3 font-sans text-sm text-content shadow-float animate-fade-in"
    >
      <Icon size={18} className={`${colorClass} shrink-0`} />
      <span className="max-w-xs sm:max-w-sm truncate text-content">{message}</span>
      <button
        type="button"
        onClick={onClose}
        aria-label="Dismiss"
        className="ml-2 shrink-0 rounded text-content-faint transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        <IconX size={16} />
      </button>
    </div>
  );
};
