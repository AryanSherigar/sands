import React from "react";
import {
  DEFAULT_NARRATION_FONT_ID,
  resolveNarrationFont,
} from "@/shared/constants/narration-fonts";
import {
  READER_FONT_SIZE_CLASSES,
  READER_LINE_HEIGHT_CLASSES,
} from "@/shared/constants/reader-preferences";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import {
  SAMPLE_PARAGRAPH,
  SAMPLE_PARAGRAPH_LABEL,
} from "../../constants/settings.constants";

export const ReadingSamplePreview: React.FC = () => {
  const theme = useReaderPreferencesStore((state) => state.theme);
  const fontId = useReaderPreferencesStore((state) => state.fontId);
  const fontSize = useReaderPreferencesStore((state) => state.fontSize);
  const lineHeight = useReaderPreferencesStore((state) => state.lineHeight);
  const font = resolveNarrationFont(fontId ?? DEFAULT_NARRATION_FONT_ID);
  const isSepia = theme === "antique-sepia";
  const themeClasses = isSepia
    ? "border-[#d8c7a8] bg-[#F4EDE0] text-[#2C2217]"
    : "border-border-subtle bg-surface-sunken text-content";

  return (
    <div
      aria-label="Live reader preview"
      className={`rounded-md border p-5 ${themeClasses}`}
    >
      <p className="mb-3 border-b border-current/10 pb-2 font-mono text-[11px] uppercase tracking-wider opacity-60">
        {SAMPLE_PARAGRAPH_LABEL}
      </p>
      <p
        className={`${font.fontClass} ${READER_FONT_SIZE_CLASSES[fontSize]} ${READER_LINE_HEIGHT_CLASSES[lineHeight]}`}
      >
        {SAMPLE_PARAGRAPH}
      </p>
    </div>
  );
};
