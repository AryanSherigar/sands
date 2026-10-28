import { ReactNode, useMemo } from "react";
import { SanityText } from "@/shared/components/reader-effects/SanityText";
import {
  findWords,
  selectDistortedWords,
  WordToken,
} from "@/shared/lib/typography/selectDistortedWords";
import { READER_FONT_SIZE_CLASSES } from "@/shared/constants/reader-preferences";
import { usePlayStore } from "../../../stores/play.store";

const DROP_CAP_CLASSES =
  "first-letter:text-3xl md:first-letter:text-4xl first-letter:font-bold first-letter:float-left first-letter:mr-2.5 first-letter:leading-none first-letter:text-inherit";
const ONE_LETTER_FIRST_WORD = /^\W*\w\b/;

function hasDropCap(paragraph: string, isFirst: boolean): boolean {
  return isFirst && !ONE_LETTER_FIRST_WORD.test(paragraph);
}

interface ParagraphDistortion {
  playthroughId: string;
  turnNumber: number;
  paragraphIndex: number;
  isComplete: boolean;
}

export interface HighlightedParagraphProps {
  paragraph: string;
  isFirst: boolean;
  fontClass: string;
  distortion?: ParagraphDistortion;
  trailing?: ReactNode;
}

export function HighlightedParagraph({
  paragraph,
  isFirst,
  fontClass,
  distortion,
  trailing,
}: HighlightedParagraphProps) {
  const fontSize = usePlayStore((s) => s.reader_font_size);
  const distortedWords = useDistortedWords(paragraph, distortion);
  const parts = (
    <SanityText
      text={paragraph}
      offset={0}
      distortedWords={distortedWords}
    />
  );
  const dropCapClass = hasDropCap(paragraph, isFirst) ? DROP_CAP_CLASSES : "";

  return (
    <p
      className={`${fontClass} ${READER_FONT_SIZE_CLASSES[fontSize]} leading-relaxed mb-4 ${dropCapClass}`}
    >
      {parts}
      {trailing}
    </p>
  );
}

function useDistortedWords(
  paragraph: string,
  distortion: ParagraphDistortion | undefined,
): WordToken[] {
  const playthroughId = distortion?.playthroughId;
  const turnNumber = distortion?.turnNumber ?? 0;
  const paragraphIndex = distortion?.paragraphIndex ?? 0;
  const isComplete = distortion?.isComplete ?? true;

  return useMemo(() => {
    if (playthroughId === undefined) return [];
    const picked = selectDistortedWords(paragraph, playthroughId, turnNumber, {
      paragraphIndex,
      isComplete,
    });
    return findWords(paragraph).filter((word) => picked.has(word.index));
  }, [paragraph, playthroughId, turnNumber, paragraphIndex, isComplete]);
}
