import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverAccent?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      hoverAccent = false,
      className = "",
      children,
      ...rest
    },
    ref,
  ) => {
    const hoverAccentClasses = hoverAccent
      ? "hover:border-border-strong group-hover:border-t-2 group-hover:border-t-(--accent)"
      : "";

    return (
      <div
        ref={ref}
        className={`rounded-md border border-border-subtle bg-surface-raised p-4 text-content transition duration-base ${hoverAccentClasses} ${className}`}
        {...rest}
      >
        {children}
      </div>
    );
  },
);

Card.displayName = "Card";
