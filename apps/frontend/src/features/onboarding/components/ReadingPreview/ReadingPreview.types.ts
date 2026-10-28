import type {
  ReaderFontSize,
  ReaderLineHeight,
  ReaderTheme,
} from "@/shared/types/readerPreferences.types";

export interface ReadingPreviewProps {
  theme: ReaderTheme;
  fontId: string | null;
  fontSize: ReaderFontSize;
  lineHeight: ReaderLineHeight;
}
