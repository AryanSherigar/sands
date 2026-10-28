import type {
  ReaderFontSize,
  ReaderLineHeight,
  ReaderTheme,
} from "@/shared/types/readerPreferences.types";

export const READER_THEME_STORAGE_KEY = "sands_reader_theme";
export const READER_FONT_SIZE_STORAGE_KEY = "sands_reader_font_size";
export const READER_LINE_HEIGHT_STORAGE_KEY = "sands_reader_line_height";

export const REDUCE_SENSORY_EFFECTS_STORAGE_KEY =
  "sands_reduce_sensory_effects";
export const REDUCED_MOTION_MEDIA_QUERY = "(prefers-reduced-motion: reduce)";
// The "Effects" switch is only offered when a scenario uses at least one tool
// that has effects to reduce.
export const EFFECT_TOOL_KEYS: readonly string[] = [
  "atmosphere",
  "rule_checks",
  "composure",
  "status_hud",
];

export const READER_THEMES: ReaderTheme[] = ["dark-velvet", "antique-sepia"];
export const DEFAULT_READER_THEME: ReaderTheme = "dark-velvet";

export const READER_FONT_SIZES: ReaderFontSize[] = [
  "small",
  "medium",
  "large",
  "extra-large",
];
export const DEFAULT_READER_FONT_SIZE: ReaderFontSize = "medium";

export const READER_FONT_SIZE_LABELS: Record<ReaderFontSize, string> = {
  small: "Small",
  medium: "Medium",
  large: "Large",
  "extra-large": "Extra Large",
};

export const READER_FONT_SIZE_CLASSES: Record<ReaderFontSize, string> = {
  small: "text-base",
  medium: "text-lg",
  large: "text-[22px]",
  "extra-large": "text-[26px]",
};

export const READER_THEME_LABELS: Record<ReaderTheme, string> = {
  "dark-velvet": "Dark",
  "antique-sepia": "Sepia",
};

export const READER_LINE_HEIGHTS: ReaderLineHeight[] = [
  "compact",
  "comfortable",
  "relaxed",
];
export const DEFAULT_READER_LINE_HEIGHT: ReaderLineHeight = "comfortable";

export const READER_LINE_HEIGHT_LABELS: Record<ReaderLineHeight, string> = {
  compact: "Compact",
  comfortable: "Comfortable",
  relaxed: "Relaxed",
};

export const READER_LINE_HEIGHT_CLASSES: Record<ReaderLineHeight, string> = {
  compact: "leading-normal",
  comfortable: "leading-[1.7]",
  relaxed: "leading-[1.9]",
};
