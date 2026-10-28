import React, { useEffect, useRef } from "react";
import type { StepHeadingProps } from "./StepHeading.types";

export const StepHeading: React.FC<StepHeadingProps> = ({
  id,
  children,
  className = "",
}) => {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <h1
      ref={headingRef}
      id={id}
      tabIndex={-1}
      className={`font-display font-semibold tracking-tight text-content focus:outline-hidden ${className}`}
    >
      {children}
    </h1>
  );
};
