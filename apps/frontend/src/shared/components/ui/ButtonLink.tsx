import React from "react";
import { Link } from "react-router-dom";
import {
  BUTTON_BASE_CLASSES,
  SIZE_CLASSES,
  VARIANT_CLASSES,
  type ButtonSize,
  type ButtonVariant,
} from "./Button.constants";

export interface ButtonLinkProps {
  to: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: React.ReactNode;
}

export const ButtonLink: React.FC<ButtonLinkProps> = ({
  to,
  variant = "secondary",
  size = "md",
  className = "",
  children,
}) => (
  <Link
    to={to}
    className={`${BUTTON_BASE_CLASSES} ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
  >
    {children}
  </Link>
);
