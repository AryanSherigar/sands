import { usePlayStore } from "../../../stores/play.store";
import { EBookTheme } from "../../../types/play.types";

export interface EBookThemeTokens {
  isSepia: boolean;
  headerBg: string;
  panelBg: string;
  cardBg: string;
  primaryButton: string;
  accentBorder: string;
  badgeBg: string;
  mutedText: string;
}

const EBOOK_THEME_TOKENS: Record<EBookTheme, EBookThemeTokens> = {
  "dark-velvet": {
    isSepia: false,
    headerBg: "bg-surface-sunken/95 border-border-subtle text-content",
    panelBg: "bg-surface-sunken border-border-subtle text-content",
    cardBg: "bg-surface-raised border-border-subtle",
    primaryButton: "bg-primary hover:bg-content text-primary-contrast",
    accentBorder: "border-border-strong",
    badgeBg: "bg-surface-raised border-border-strong text-content",
    mutedText: "text-content-muted",
  },
  "antique-sepia": {
    isSepia: true,
    headerBg: "bg-[#faf4e8]/95 border-[#d8c7a8] text-[#2c2217]",
    panelBg: "bg-[#faf4e8] border-[#d8c7a8] text-[#2c2217]",
    cardBg: "bg-[#f5ebd7] border-[#e2d5be]",
    primaryButton: "bg-[#2c2217] hover:bg-[#433523] text-[#faf4e8]",
    accentBorder: "border-[#2c2217]",
    badgeBg: "bg-[#f5ebd7] border-[#d8c7a8] text-[#2c2217]",
    mutedText: "text-[#6b5c45]",
  },
};

export function useEBookThemeTokens(): EBookThemeTokens {
  const theme = usePlayStore((s) => s.ebook_theme);
  return EBOOK_THEME_TOKENS[theme];
}
