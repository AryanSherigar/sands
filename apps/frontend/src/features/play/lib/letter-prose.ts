const PARAGRAPH_BREAK = /\n\s*\n/;

export const splitProse = (prose: string): string[] => {
  const paragraphs = prose
    .split(PARAGRAPH_BREAK)
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0);
  return paragraphs.length > 0 ? paragraphs : [""];
};

export const joinProse = (paragraphs: string[]): string =>
  paragraphs
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0)
    .join("\n\n");
