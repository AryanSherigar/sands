import { useMutation } from "@tanstack/react-query";
import { submitAlphaSurvey } from "@/shared/api/alphaSurvey.api";
import type {
  AlphaSurveyAccepted,
  AlphaSurveyRequest,
} from "@/shared/types/alphaSurvey.types";

export function useSubmitSurvey() {
  return useMutation<AlphaSurveyAccepted, Error, AlphaSurveyRequest>({
    mutationFn: submitAlphaSurvey,
  });
}
