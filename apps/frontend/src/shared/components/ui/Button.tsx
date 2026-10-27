import React from "react";
import {
  BUTTON_BASE_CLASSES,
  SIZE_CLASSES,
  VARIANT_CLASSES,
} from "./Button.constants";
import type { ButtonSize, ButtonVariant } from "./Button.constants";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      disabled = false,
      className = "",
      children,
      ...rest
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled}
        className={`${BUTTON_BASE_CLASSES} ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
