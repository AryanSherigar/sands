import { ReaderTheme } from "@/shared/types/readerPreferences.types";

export interface ReaderVignetteProps {
  strength: number;
  theme: ReaderTheme;
  shouldAnimate: boolean;
}
