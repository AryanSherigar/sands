import React, { useId } from "react";
import { ReaderVignetteProps } from "./ReaderVignette.types";

const CLEAR_RADIUS_PERCENT = 45;

// Darkens the edges of the reader as tension rises. Purely decorative: it is
// hidden from assistive technology and never takes pointer events. Opacity is
// an SVG attribute, so no inline style is needed.
export const ReaderVignette: React.FC<ReaderVignetteProps> = ({
  strength,
  theme,
  shouldAnimate,
}) => {
  const gradientId = useId();

  return (
    <svg
      aria-hidden="true"
      data-theme={theme}
      className="reader-vignette pointer-events-none fixed inset-0 z-10 h-full w-full"
      preserveAspectRatio="none"
    >
      <defs>
        <radialGradient id={gradientId} cx="50%" cy="50%" r="75%">
          <stop offset={`${CLEAR_RADIUS_PERCENT}%`} className="vignette-stop-clear" />
          <stop offset="100%" className="vignette-stop-dark" />
        </radialGradient>
      </defs>
      <rect
        width="100%"
        height="100%"
        fill={`url(#${gradientId})`}
        fillOpacity={strength}
        className={shouldAnimate ? "vignette-fill-animated" : undefined}
      />
    </svg>
  );
};
