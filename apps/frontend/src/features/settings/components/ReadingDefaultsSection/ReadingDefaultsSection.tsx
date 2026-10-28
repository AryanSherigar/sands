import React, { useEffect } from "react";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { useVoiceOutputPreference } from "@/shared/hooks/useVoiceOutputPreference";
import {
  FONT_GENRE_CATEGORIES,
  NARRATION_FONTS_CATALOG,
  resolveNarrationFont,
} from "@/shared/constants/narration-fonts";
import {
  READER_FONT_SIZES,
  READER_LINE_HEIGHTS,
  READER_THEMES,
  READER_THEME_LABELS,
} from "@/shared/constants/reader-preferences";
import { loadNarrationFont } from "@/shared/lib/font-loader";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type {
  ReaderFontSize,
  ReaderLineHeight,
  ReaderTheme,
} from "@/shared/types/readerPreferences.types";
import {
  AMBIENCE_VOLUME_STEP,
  LINE_HEIGHT_OPTION_LABELS,
  PERCENT_MULTIPLIER,
  READER_FONT_SIZE_PIXELS,
  STORY_FONT_OPTION_LABEL,
  STORY_FONT_OPTION_VALUE,
} from "../../constants/settings.constants";
import { useAmbiencePreference } from "../../hooks/useAmbiencePreference";
import { OptionGroup } from "../OptionGroup/OptionGroup";
import { ReadingSamplePreview } from "../ReadingSamplePreview/ReadingSamplePreview";
import { SettingsSwitch } from "../SettingsSwitch/SettingsSwitch";

const THEME_OPTIONS = READER_THEMES.map((theme) => ({
  value: theme,
  label: READER_THEME_LABELS[theme],
}));
const SIZE_OPTIONS = READER_FONT_SIZES.map((size) => ({
  value: size,
  label: `${size[0].toUpperCase()}${size.slice(1)} (${READER_FONT_SIZE_PIXELS[size]})`,
}));
const LINE_HEIGHT_OPTIONS = READER_LINE_HEIGHTS.filter(
  (height) => height in LINE_HEIGHT_OPTION_LABELS,
).map((height) => ({ value: height, label: LINE_HEIGHT_OPTION_LABELS[height] }));

export const ReadingDefaultsSection: React.FC = () => {
  const preferences = useReaderPreferencesStore();
  const ambience = useAmbiencePreference();
  const voice = useVoiceOutputPreference();
  const isAlphaMode = useIsAlphaMode();
  const activeFontId = preferences.fontId ?? STORY_FONT_OPTION_VALUE;

  useEffect(() => {
    loadNarrationFont(resolveNarrationFont(preferences.fontId).id);
  }, [preferences.fontId]);

  return (
    <div className="space-y-5 rounded-md border border-border-subtle bg-surface-raised p-5">
      <OptionGroup
        label="Reading theme"
        options={THEME_OPTIONS}
        value={preferences.theme}
        onChange={(value) => preferences.setTheme(value as ReaderTheme)}
      />
      <OptionGroup
        label="Text size"
        options={SIZE_OPTIONS}
        value={preferences.fontSize}
        onChange={(value) => preferences.setFontSize(value as ReaderFontSize)}
      />
      <OptionGroup
        label="Line height"
        options={LINE_HEIGHT_OPTIONS}
        value={preferences.lineHeight}
        onChange={(value) =>
          preferences.setLineHeight(value as ReaderLineHeight)
        }
      />
      <div className="space-y-2">
        <label
          htmlFor="narration-font"
          className="block font-sans text-xs font-medium text-content-muted"
        >
          Narration typography
        </label>
        <select
          id="narration-font"
          value={activeFontId}
          onChange={(event) => {
            const next = event.target.value;
            preferences.setFontId(next === STORY_FONT_OPTION_VALUE ? null : next);
          }}
          className="h-10 w-full rounded-sm border border-border-strong bg-surface-inset px-3 font-sans text-sm text-content focus-visible:border-primary focus-visible:outline-hidden"
        >
          <option value={STORY_FONT_OPTION_VALUE}>{STORY_FONT_OPTION_LABEL}</option>
          {FONT_GENRE_CATEGORIES.map((category) => (
            <optgroup key={category} label={category}>
              {NARRATION_FONTS_CATALOG.filter(
                (font) => font.category === category,
              ).map((font) => (
                <option key={font.id} value={font.id}>
                  {font.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
      <div className="space-y-4 border-t border-border-subtle pt-5">
        <h3 className="font-mono text-[11px] uppercase tracking-wider text-content-faint">
          Audio &amp; narration
        </h3>
        {!isAlphaMode && (
          <SettingsSwitch
            id="voice-narration"
            label="Voice narration stream"
            description="Experimental text-to-speech for story turns."
            isChecked={voice.isVoiceOutputEnabled}
            isDisabled={voice.isLoading || voice.isUpdating}
            onChange={voice.setVoiceOutputEnabled}
          />
        )}
        <SettingsSwitch
          id="ambience"
          label="Background scenario ambience"
          description="Subtle atmospheric soundtrack for each scene."
          isChecked={ambience.isAmbienceEnabled}
          onChange={ambience.setAmbienceEnabled}
        />
        <div className="space-y-1">
          <label
            htmlFor="ambience-volume"
            className="flex justify-between font-sans text-xs text-content-muted"
          >
            <span>Ambience volume</span>
            <span>{Math.round(ambience.volume * PERCENT_MULTIPLIER)}%</span>
          </label>
          <input
            id="ambience-volume"
            type="range"
            min={0}
            max={PERCENT_MULTIPLIER}
            step={AMBIENCE_VOLUME_STEP}
            value={Math.round(ambience.volume * PERCENT_MULTIPLIER)}
            onChange={(event) =>
              ambience.setVolume(Number(event.target.value) / PERCENT_MULTIPLIER)
            }
            className="h-6 w-full accent-primary"
          />
        </div>
      </div>
      <div className="space-y-2 border-t border-border-subtle pt-5">
        <h3 className="font-sans text-sm font-medium text-content">Live reader preview</h3>
        <ReadingSamplePreview />
      </div>
    </div>
  );
};
