import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { IconX } from "@tabler/icons-react";
import { useFocusTrap } from "@/shared/hooks/useFocusTrap";
import type { ModalProps, ModalSize } from "./Modal.types";

export type { ModalProps } from "./Modal.types";

const SIZE_CLASSES: Record<ModalSize, string> = {
  default: "max-w-lg",
  narrow: "max-w-[440px]",
};

const SHEET_BACKDROP_CLASSES = "items-end sm:items-center p-0 sm:p-4";
const SHEET_PANEL_CLASSES = "rounded-b-none sm:rounded-b-lg";

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  isDismissible = true,
  size = "default",
  isSheetOnMobile = false,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, isOpen);

  useEffect(() => {
    if (!isOpen || !isDismissible) return undefined;
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isDismissible, onClose]);

  if (!isOpen) return null;

  const handleBackdropClick = (
    event: React.MouseEvent<HTMLDivElement>,
  ): void => {
    if (isDismissible && event.target === event.currentTarget) onClose();
  };

  const backdropLayout = isSheetOnMobile
    ? SHEET_BACKDROP_CLASSES
    : "items-center justify-center p-4";
  const panelShape = isSheetOnMobile ? SHEET_PANEL_CLASSES : "";

  return createPortal(
    <div
      className={`fixed inset-0 z-50 flex bg-black/75 backdrop-blur-xs ${backdropLayout}`}
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`animate-modal-in flex max-h-[90vh] w-full ${SIZE_CLASSES[size]} ${panelShape} flex-col rounded-lg border border-border-strong bg-surface-overlay p-6 font-sans text-content shadow-modal focus:outline-hidden`}
      >
        {title && (
          <div className="flex shrink-0 items-center justify-between pb-4 border-b border-border-subtle">
            <h2 className="text-sm font-semibold text-content">{title}</h2>
            {isDismissible && (
              <button
                onClick={onClose}
                aria-label="Close"
                className="flex h-7 w-7 items-center justify-center rounded-md text-content-faint transition hover:bg-surface-raised hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary/20"
              >
                <IconX size={16} />
              </button>
            )}
          </div>
        )}
        <div className={`overflow-y-auto ${title ? "pt-4" : ""}`}>{children}</div>
      </div>
    </div>,
    document.body,
  );
};
