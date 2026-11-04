export interface CouncilDialogueLine {
  speaker: string;
  text: string;
}

export const COUNCIL_FALLBACK_SPEAKER = "COUNCIL";
export const SOVEREIGN_SPEAKER = "SOVEREIGN";

const MINISTER_TAG_SOURCE = "\\[(CHANCELLOR|MARSHAL|TREASURER|PRELATE)\\]:";
const TRAILING_PARTIAL_TAG = /\[[A-Z]*\]?$/;

const toLine = (speaker: string, rawText: string): CouncilDialogueLine | null => {
  const text = rawText.trim();
  return text ? { speaker, text } : null;
};

const dropIncompleteTrailingTag = (raw: string): string => raw.replace(TRAILING_PARTIAL_TAG, "");

export const parseCouncilReply = (raw: string): CouncilDialogueLine[] => {
  const pattern = new RegExp(MINISTER_TAG_SOURCE, "g");
  const source = dropIncompleteTrailingTag(raw);
  const lines: CouncilDialogueLine[] = [];
  let speaker = COUNCIL_FALLBACK_SPEAKER;
  let cursor = 0;
  let match = pattern.exec(source);
  while (match) {
    const line = toLine(speaker, source.slice(cursor, match.index));
    if (line) lines.push(line);
    speaker = match[1];
    cursor = match.index + match[0].length;
    match = pattern.exec(source);
  }
  const lastLine = toLine(speaker, source.slice(cursor));
  return lastLine ? [...lines, lastLine] : lines;
};
