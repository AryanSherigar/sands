import { useMemo } from "react";
import {
  ALWAYS_REMEMBER_KEY,
  ALWAYS_REMEMBER_MAX_LINES,
  ALWAYS_REMEMBER_MAX_LINE_LENGTH,
} from "../constants/guideLimits";
import { useGuide } from "./useGuide";
import { useSyncedValue } from "./useSyncedValue";

const NO_LINES: string[] = [];

const readLines = (stored: unknown): string[] =>
  Array.isArray(stored) && stored.every((line) => typeof line === "string")
    ? stored
    : NO_LINES;

export const useAlwaysRemember = () => {
  const { scenario, saveFields } = useGuide();
  const stored = scenario?.world_data?.[ALWAYS_REMEMBER_KEY];
  const serverLines = useMemo(() => readLines(stored), [stored]);
  const { value: lines, commit } = useSyncedValue(serverLines, (next) =>
    saveFields({
      worldData: { [ALWAYS_REMEMBER_KEY]: next.map((line) => line.trim()).filter(Boolean) },
    }),
  );

  const clamp = (line: string): string => line.slice(0, ALWAYS_REMEMBER_MAX_LINE_LENGTH);
  const canAdd = lines.length < ALWAYS_REMEMBER_MAX_LINES;

  return {
    lines,
    canAdd,
    addLine: (line: string): void => {
      if (canAdd) commit([...lines, clamp(line)]);
    },
    editLine: (index: number, line: string): void =>
      commit(lines.map((existing, lineIndex) => (lineIndex === index ? clamp(line) : existing))),
    removeLine: (index: number): void =>
      commit(lines.filter((_, lineIndex) => lineIndex !== index)),
  };
};
