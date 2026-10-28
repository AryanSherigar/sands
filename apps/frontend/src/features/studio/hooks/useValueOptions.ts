import type { ValueOption } from "../types/sentence.types";
import { useValueOptionsState } from "./useValueOptionsState";

export const useValueOptions = (): ValueOption[] => useValueOptionsState().options;
