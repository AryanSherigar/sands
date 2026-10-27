import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ error, className = "", id, ...rest }, ref) => {
    const hasError = Boolean(error);

    return (
      <div className="w-full">
        <input
          ref={ref}
          id={id}
          className={`h-10 w-full rounded-sm border bg-surface-inset px-3 text-sm text-content placeholder:text-content-faint transition duration-base focus:border-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50 ${
            hasError ? "border-danger text-content" : "border-border-strong"
          } ${className}`}
          aria-invalid={hasError}
          {...rest}
        />
        {hasError && <p className="mt-1 text-micro text-danger">{error}</p>}
      </div>
    );
  },
);

Input.displayName = "Input";
