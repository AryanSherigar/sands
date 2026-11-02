export type CourtLine =
  | { kind: "narration"; text: string }
  | { kind: "speech"; speaker: string; text: string };

const SPEAKER_PATTERN = /^([A-Z][A-Z .'-]{1,39}):\s*(.+)$/;
const QUOTE_EDGES = /^["“]|["”]$/g;

const toTitleCase = (name: string): string =>
  name
    .toLowerCase()
    .split(" ")
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");

const parseLine = (line: string): CourtLine => {
  const match = SPEAKER_PATTERN.exec(line);
  if (!match) return { kind: "narration", text: line };
  return {
    kind: "speech",
    speaker: toTitleCase(match[1].trim()),
    text: match[2].replace(QUOTE_EDGES, "").trim(),
  };
};

export const parseCourtText = (text: string): CourtLine[] =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map(parseLine);
