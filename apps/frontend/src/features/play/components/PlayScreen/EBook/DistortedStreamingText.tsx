import { DistortedStreamingTextProps } from "./DistortedStreamingText.types";
import { HighlightedParagraph } from "./HighlightedParagraph";

const PARAGRAPH_BREAK = /\n\s*\n/;

/**
 * The streaming chapter while a sanity band is active. It uses the same word
 * selection as a finished turn (same paragraph split, same turn number), so a
 * word that distorts while it streams in keeps its look when the chapter lands.
 */
export function DistortedStreamingText({
  text,
  fontClass,
  turnNumber,
  playthroughId,
}: DistortedStreamingTextProps) {
  const paragraphs = text.split(PARAGRAPH_BREAK).filter(Boolean);
  const lastIndex = paragraphs.length - 1;

  return (
    <>
      {paragraphs.map((paragraph, idx) => (
        <HighlightedParagraph
          key={idx}
          paragraph={paragraph}
          isFirst={false}
          fontClass={fontClass}
          distortion={{
            playthroughId,
            turnNumber,
            paragraphIndex: idx,
            isComplete: idx !== lastIndex,
          }}
          trailing={
            idx === lastIndex ? (
              <span className="inline-block w-0.5 h-4 ml-1 bg-accent animate-pulse align-middle" />
            ) : undefined
          }
        />
      ))}
    </>
  );
}
