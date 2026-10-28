import { useMutation } from "@tanstack/react-query";
import { submitAlphaFeedback } from "../api/alphaFeedback.api";
import type { AlphaFeedbackRequest } from "../types/alphaFeedback.types";

export function useSubmitFeedback() {
  return useMutation<void, Error, AlphaFeedbackRequest>({
    mutationFn: submitAlphaFeedback,
  });
}
