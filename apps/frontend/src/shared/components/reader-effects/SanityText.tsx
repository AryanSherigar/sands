import React from "react";
import { SanityTextProps } from "./SanityText.types";

// A plain stretch of paragraph text that starts at `offset` in the paragraph.
// Words picked for distortion render in the eerie face; the rest is untouched.
export const SanityText: React.FC<SanityTextProps> = ({
  text,
  offset,
  distortedWords,
}) => {
  const end = offset + text.length;
  const inside = distortedWords.filter(
    (word) => word.start >= offset && word.end <= end,
  );
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (const word of inside) {
    const start = word.start - offset;
    if (start > cursor) nodes.push(text.slice(cursor, start));
    nodes.push(
      <span key={word.index} className="font-eerie">
        {text.slice(start, word.end - offset)}
      </span>,
    );
    cursor = word.end - offset;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return <>{nodes}</>;
};
