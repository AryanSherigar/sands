import React from "react";
import {
  DEFAULT_NARRATION_FONT_ID,
  resolveNarrationFont,
} from "@/shared/constants/narration-fonts";
import {
  READER_FONT_SIZE_CLASSES,
  READER_LINE_HEIGHT_CLASSES,
} from "@/shared/constants/reader-preferences";
import type { ReadingPreviewProps } from "./ReadingPreview.types";

export const ReadingPreview: React.FC<ReadingPreviewProps> = ({
  theme,
  fontId,
  fontSize,
  lineHeight,
}) => {
  const activeFont = resolveNarrationFont(fontId ?? DEFAULT_NARRATION_FONT_ID);
  const isSepia = theme === "antique-sepia";

  const containerThemeClasses = isSepia
    ? "border-[#d8c7a8] bg-[#F4EDE0] text-[#2C2217]"
    : "border-border-subtle bg-surface-sunken text-content";

  const metaClasses = isSepia ? "text-[#6E5C49]" : "text-content-faint";
  const entityClasses = isSepia
    ? "border-[#7E5332] text-[#2C2217]"
    : "border-[#C79A74] text-content";

  return (
    <div
      className={`relative rounded-xl border p-6 shadow-inner transition-colors duration-200 ${containerThemeClasses}`}
    >
      {/* Specimen Header */}
      <div
        className={`mb-4 flex items-center justify-between border-b pb-3 font-mono text-xs ${
          isSepia ? "border-[#d8c7a8]/60" : "border-border-subtle"
        } ${metaClasses}`}
      >
        <div className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full bg-[#C79A74]"
            aria-hidden="true"
          />
          <span className="font-medium">The Grey Ledger · Turn 14</span>
        </div>
        <span className="text-[11px]">Measure: 68ch max</span>
      </div>

      {/* Dynamic Specimen Text */}
      <div
        data-testid="reader-preview"
        aria-live="polite"
        className={`mx-auto max-w-[68ch] transition-all ${activeFont.fontClass} ${READER_FONT_SIZE_CLASSES[fontSize]} ${READER_LINE_HEIGHT_CLASSES[lineHeight]}`}
      >
        <p className="mb-4">
          “Detective Vane leans against the rain-slicked brickwork of Wharf 7,
          listening for the cadence of the informant&apos;s limp. Steam curls off
          the river channel like white wool, smelling faintly of sulfur and cold
          harbor mud.”
        </p>
        <p className="mb-4">
          “He reaches into his trench coat for the{" "}
          <span
            className={`border-b border-dotted pb-0.5 font-medium ${entityClasses}`}
          >
            copper token
          </span>{" "}
          recovered from the municipal archive. In the dull streetlight, the
          cipher stamped into its rim seems to hum with quiet, deterministic
          precision.”
        </p>
        <p className={`text-sm italic ${isSepia ? "text-[#6E5C49]" : "text-content-muted"}`}>
          What do you do next? Await the footsteps at the crane ladder, or slip
          inside the drydock before the fog burns off?
        </p>
      </div>
    </div>
  );
};
