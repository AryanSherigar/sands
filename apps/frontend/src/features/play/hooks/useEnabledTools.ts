import { usePlayStore } from "../stores/play.store";

const NO_TOOLS: string[] = [];

export const useEnabledTools = (): string[] =>
  usePlayStore((state) => state.playthrough?.enabled_tools ?? NO_TOOLS);
