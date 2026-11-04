export interface BookExportInput {
  rulerName: string;
  chroniclerName: string;
  chroniclerTitle: string;
  eraLabel: string;
  chapters: string[];
  closingEntry: string;
}

export function composeBookText(input: BookExportInput): string {
  const header = [
    input.rulerName,
    `${input.eraLabel}`,
    `Written by ${input.chroniclerName}, ${input.chroniclerTitle}`,
  ].join("\n");
  const parts = [header, ...input.chapters, input.closingEntry];
  return parts.map((part) => part.trim()).filter((part) => part.length > 0).join("\n\n");
}

export const bookFileName = (rulerName: string): string => {
  const slug = rulerName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${slug || "chronicle"}-chronicle.txt`;
};
