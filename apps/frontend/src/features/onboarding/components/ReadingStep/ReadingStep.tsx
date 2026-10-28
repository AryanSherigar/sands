import React, { useEffect } from "react";
import { Button } from "@/shared/components/ui/Button";
import {
  DEFAULT_NARRATION_FONT_ID,
  NARRATION_FONTS_CATALOG,
  resolveNarrationFont,
} from "@/shared/constants/narration-fonts";
import {
  READER_FONT_SIZES,
  READER_FONT_SIZE_LABELS,
  READER_LINE_HEIGHTS,
  READER_LINE_HEIGHT_LABELS,
  READER_THEMES,
  READER_THEME_LABELS,
} from "@/shared/constants/reader-preferences";
import { loadNarrationFont } from "@/shared/lib/font-loader";
import { useOnboardingStore } from "../../stores/onboarding.store";
import { ReadingPreview } from "../ReadingPreview/ReadingPreview";
import { StepFooter } from "../StepFooter/StepFooter";
import { StepHeading } from "../StepHeading/StepHeading";
import type { ReadingStepProps } from "./ReadingStep.types";

const SIZE_NUMBERS: Record<string, string> = {
  small: "16",
  medium: "18",
  large: "22",
};

const LEADING_SHORTHAND: Record<string, string> = {
  compact: "Compact",
  comfortable: "1.7 Comf",
  relaxed: "1.9 Relax",
};

export const ReadingStep: React.FC<ReadingStepProps> = ({
  onFinish,
  onBack,
  onSkip,
  isSaving,
  errorMessage,
}) => {
  const theme = useOnboardingStore((state) => state.readerTheme);
  const fontId = useOnboardingStore((state) => state.readerFontId);
  const fontSize = useOnboardingStore((state) => state.readerFontSize);
  const setTheme = useOnboardingStore((state) => state.setReaderTheme);
  const setFontId = useOnboardingStore((state) => state.setReaderFontId);
  const setFontSize = useOnboardingStore((state) => state.setReaderFontSize);
  const lineHeight = useOnboardingStore((state) => state.readerLineHeight);
  const setLineHeight = useOnboardingStore(
    (state) => state.setReaderLineHeight,
  );
  const activeFont = resolveNarrationFont(fontId ?? DEFAULT_NARRATION_FONT_ID);

  useEffect(() => {
    loadNarrationFont(activeFont.id);
  }, [activeFont.id]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onFinish();
  };

  return (
    <form aria-labelledby="onboarding-reading-title" onSubmit={handleSubmit}>
      <div className="mb-5">
        <span className="mb-1 block font-mono text-xs uppercase tracking-wider text-content-faint">
          Step 3 of 3
        </span>
        <StepHeading
          id="onboarding-reading-title"
          className="text-2xl md:text-3xl"
        >
          How do you like to read?
        </StepHeading>
        <p className="mt-1 text-sm text-content-muted">
          Adjust theme, typography and measure. Preview updates live.
        </p>
      </div>

      {/* 4 Controls Bar */}
      <div className="mb-5 grid grid-cols-1 gap-3 rounded-lg border border-border-subtle bg-surface-raised p-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* 1. Theme toggle (Dark vs Sepia) */}
        <div>
          <label className="mb-1.5 block font-mono text-[11px] text-content-faint">
            Theme
          </label>
          <div
            role="group"
            aria-label="Reader theme"
            className="flex items-center rounded-md border border-border-strong bg-surface-inset p-0.5"
          >
            {READER_THEMES.map((option) => {
              const isSelected = theme === option;
              return (
                <button
                  key={option}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setTheme(option)}
                  className={`flex-1 rounded py-1 text-center text-xs font-medium transition-colors ${
                    isSelected
                      ? "bg-primary font-semibold text-primary-contrast"
                      : "text-content-muted hover:text-content"
                  }`}
                >
                  {READER_THEME_LABELS[option]}
                </button>
              );
            })}
          </div>
        </div>

        {/* 2. Text Size */}
        <div>
          <label className="mb-1.5 block font-mono text-[11px] text-content-faint">
            Text size
          </label>
          <div
            role="group"
            aria-label="Text size"
            className="flex items-center rounded-md border border-border-strong bg-surface-inset p-0.5"
          >
            {READER_FONT_SIZES.map((option) => {
              const isSelected = fontSize === option;
              return (
                <button
                  key={option}
                  type="button"
                  aria-label={READER_FONT_SIZE_LABELS[option]}
                  aria-pressed={isSelected}
                  onClick={() => setFontSize(option)}
                  className={`flex-1 rounded py-1 text-center font-mono text-xs transition-colors ${
                    isSelected
                      ? "bg-primary font-semibold text-primary-contrast"
                      : "text-content-muted hover:text-content"
                  }`}
                >
                  {SIZE_NUMBERS[option] ?? option}
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Line Height / Spacing */}
        <div>
          <label className="mb-1.5 block font-mono text-[11px] text-content-faint">
            Line spacing
          </label>
          <div
            role="group"
            aria-label="Line height"
            className="flex items-center rounded-md border border-border-strong bg-surface-inset p-0.5"
          >
            {READER_LINE_HEIGHTS.map((option) => {
              const isSelected = lineHeight === option;
              return (
                <button
                  key={option}
                  type="button"
                  aria-label={READER_LINE_HEIGHT_LABELS[option]}
                  aria-pressed={isSelected}
                  onClick={() => setLineHeight(option)}
                  className={`flex-1 rounded py-1 text-center text-xs transition-colors ${
                    isSelected
                      ? "bg-primary font-semibold text-primary-contrast"
                      : "text-content-muted hover:text-content"
                  }`}
                >
                  {LEADING_SHORTHAND[option] ?? option}
                </button>
              );
            })}
          </div>
        </div>

        {/* 4. Narration Font */}
        <div>
          <label
            htmlFor="onboarding-font"
            className="mb-1.5 block font-mono text-[11px] text-content-faint"
          >
            Narration font
          </label>
          <select
            id="onboarding-font"
            value={activeFont.id}
            onChange={(event) => setFontId(event.target.value)}
            className="w-full rounded-md border border-border-strong bg-surface-inset px-2.5 py-1 text-xs font-medium text-content transition-colors focus:border-primary focus:outline-hidden"
          >
            {NARRATION_FONTS_CATALOG.map((font) => (
              <option key={font.id} value={font.id}>
                {font.label} ({font.category})
              </option>
            ))}
          </select>
        </div>
      </div>

      <ReadingPreview
        theme={theme}
        fontId={fontId}
        fontSize={fontSize}
        lineHeight={lineHeight}
      />

      {errorMessage && (
        <div
          role="alert"
          className="mt-4 flex items-center gap-3 text-sm text-danger"
        >
          <p>{errorMessage}</p>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onFinish}
          >
            Retry
          </Button>
        </div>
      )}

      <StepFooter
        onBack={onBack}
        onSkip={onSkip}
        onNext={onFinish}
        isBusy={isSaving}
      />
    </form>
  );
};
