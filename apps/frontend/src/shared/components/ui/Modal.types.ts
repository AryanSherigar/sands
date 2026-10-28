import type React from "react";

export type ModalSize = "default" | "narrow";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  isDismissible?: boolean;
  size?: ModalSize;
  isSheetOnMobile?: boolean;
}
