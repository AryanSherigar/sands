import React, { useEffect, useRef, useState } from "react";
import { usePlayStore } from "../../../stores/play.store";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import {
  FONT_GENRE_CATEGORIES,
  NARRATION_FONTS_CATALOG,
  resolveNarrationFont,
} from "@/shared/constants/narration-fonts";
import {
  EFFECT_TOOL_KEYS,
  READER_FONT_SIZES,
  READER_FONT_SIZE_LABELS,
  READER_LINE_HEIGHTS,
  READER_LINE_HEIGHT_LABELS,
} from "@/shared/constants/reader-preferences";
import { loadNarrationFont } from "@/shared/lib/font-loader";
import { useEnabledTools } from "../../../hooks/useEnabledTools";
import { ReaderTypographyMenuProps } from "./ReaderTypographyMenu.types";

export const ReaderTypographyMenu: React.FC<ReaderTypographyMenuProps> = ({
  isSepia = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const scenarioFont = usePlayStore((s) => s.playthrough?.narration_font);
  const readerFontOverride = usePlayStore((s) => s.reader_font_override);
  const setReaderFontOverride = usePlayStore((s) => s.setReaderFontOverride);

  const currentFontSize = useReaderPreferencesStore((s) => s.fontSize);
  const setFontSize = useReaderPreferencesStore((s) => s.setFontSize);
  const currentLineHeight = useReaderPreferencesStore((s) => s.lineHeight);
  const setLineHeight = useReaderPreferencesStore((s) => s.setLineHeight);

  const reduceSensoryEffects = useReaderPreferencesStore(
    (s) => s.reduceSensoryEffects,
  );
  const setReduceSensoryEffects = useReaderPreferencesStore(
    (s) => s.setReduceSensoryEffects,
  );
  const enabledTools = useEnabledTools();
  const hasEffects = enabledTools.some((key) => EFFECT_TOOL_KEYS.includes(key));

  const handleReduceEffectsChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setReduceSensoryEffects(e.target.checked);
  };

  const defaultFontDef = resolveNarrationFont(scenarioFont);
  const effectiveFontDef = resolveNarrationFont(
    readerFontOverride ?? scenarioFont,
  );

  useEffect(() => {
    loadNarrationFont(effectiveFontDef.id);
  }, [effectiveFontDef.id]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleFontChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    const nextOverride = value === "default" ? null : value;
    setReaderFontOverride(nextOverride);
    loadNarrationFont(nextOverride ?? scenarioFont);
  };

  const popoverStyle = isSepia
    ? "bg-[#faf4e8] border-[#d8c7a8] text-[#2c2217]"
    : "bg-surface-overlay border-border-strong text-content shadow-float";

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="p-1.5 px-2.5 rounded-xl border border-inherit/20 hover:bg-surface-raised font-mono text-xs flex items-center gap-1 cursor-pointer transition-colors"
        title="Reader Typography & Font Settings"
        aria-label="Typography settings"
      >
        <span className="font-serif font-bold text-sm">Aa</span>
        <span className="hidden lg:inline text-[11px] opacity-80">
          {effectiveFontDef.label}
        </span>
      </button>

      {isOpen && (
        <div
          className={`absolute right-0 mt-2 w-72 p-3 rounded-xl border shadow-xl z-50 text-xs space-y-3 ${popoverStyle}`}
        >
          <div className="flex items-center justify-between border-b border-inherit/20 pb-2">
            <span className="font-mono font-semibold uppercase tracking-wider text-[11px]">
              Typography
            </span>
            <span className="font-mono text-[10px] opacity-70">
              {readerFontOverride ? "Custom Override" : "Scenario Default"}
            </span>
          </div>

          <div className="space-y-1">
            <label
              htmlFor="reader-font-select"
              className="font-mono text-[11px] opacity-75 block"
            >
              Narration Font
            </label>
            <select
              id="reader-font-select"
              aria-label="Reader Narration Font"
              value={readerFontOverride ?? "default"}
              onChange={handleFontChange}
              className="w-full bg-surface-inset border border-inherit/30 rounded-lg p-2 font-mono text-xs focus:outline-hidden focus:border-primary"
            >
              <option value="default">
                Scenario Default ({defaultFontDef.label})
              </option>
              {FONT_GENRE_CATEGORIES.map((category) => (
                <optgroup key={category} label={category}>
                  {NARRATION_FONTS_CATALOG.filter(
                    (f) => f.category === category,
                  ).map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-inherit/20">
            <span className="font-mono text-[11px] opacity-75 block">
              Text Size
            </span>
            <div className="grid grid-cols-4 gap-1">
              {READER_FONT_SIZES.map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => setFontSize(size)}
                  className={`py-1 px-1.5 text-center font-mono text-[10px] rounded border transition-colors cursor-pointer ${
                    currentFontSize === size
                      ? "bg-primary text-primary-contrast font-semibold border-primary"
                      : "border-inherit/30 hover:bg-surface-raised"
                  }`}
                  aria-label={READER_FONT_SIZE_LABELS[size]}
                >
                  {size === "extra-large" ? "XL" : size.charAt(0).toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-inherit/20">
            <span className="font-mono text-[11px] opacity-75 block">
              Line Spacing
            </span>
            <div className="grid grid-cols-3 gap-1">
              {READER_LINE_HEIGHTS.map((height) => (
                <button
                  key={height}
                  type="button"
                  onClick={() => setLineHeight(height)}
                  className={`py-1 px-1 text-center font-mono text-[10px] rounded border transition-colors cursor-pointer ${
                    currentLineHeight === height
                      ? "bg-primary text-primary-contrast font-semibold border-primary"
                      : "border-inherit/30 hover:bg-surface-raised"
                  }`}
                  aria-label={READER_LINE_HEIGHT_LABELS[height]}
                >
                  {READER_LINE_HEIGHT_LABELS[height]}
                </button>
              ))}
            </div>
          </div>

          {hasEffects && (
            <div className="space-y-1 pt-2 border-t border-inherit/20">
              <span className="font-mono font-semibold uppercase tracking-wider text-[11px] block">
                Effects
              </span>
              <label className="flex items-start gap-2 font-mono text-[11px] cursor-pointer">
                <input
                  type="checkbox"
                  checked={reduceSensoryEffects}
                  onChange={handleReduceEffectsChange}
                  className="mt-0.5"
                />
                <span>
                  Reduce sensory effects
                  <span className="block opacity-70">
                    Takes the clock off timed prompts, calms flicker and motion.
                  </span>
                </span>
              </label>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
