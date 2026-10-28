import { WordToken } from "@/shared/lib/typography/selectDistortedWords";

export interface SanityTextProps {
  text: string;
  offset: number;
  distortedWords: readonly WordToken[];
}
