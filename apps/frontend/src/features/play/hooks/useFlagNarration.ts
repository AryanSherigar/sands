import { useMutation } from "@tanstack/react-query";
import { flagAlphaNarration } from "../api/alphaFeedback.api";
import type { AlphaFlagRequest } from "../types/alphaFeedback.types";

interface FlagNarrationVariables {
  turnId: string;
  request: AlphaFlagRequest;
}

export function useFlagNarration() {
  return useMutation<void, Error, FlagNarrationVariables>({
    mutationFn: ({ turnId, request }) => flagAlphaNarration(turnId, request),
  });
}
