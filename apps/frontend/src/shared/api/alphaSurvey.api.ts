import { isAxiosError } from "axios";
import { apiClient } from "@/shared/lib/api-client";
import type {
  AlphaSurveyAccepted,
  AlphaSurveyRequest,
} from "@/shared/types/alphaSurvey.types";

const SURVEY_ENDPOINT = "/v1/alpha/survey";
const HTTP_CONFLICT = 409;

/** A second submission is a 409; the survey is already answered, so the
 * caller treats it as done. */
export const submitAlphaSurvey = async (
  request: AlphaSurveyRequest,
): Promise<AlphaSurveyAccepted> => {
  try {
    const response = await apiClient.post<AlphaSurveyAccepted>(
      SURVEY_ENDPOINT,
      request,
    );
    return response.data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === HTTP_CONFLICT) {
      return { kind: request.kind };
    }
    throw error;
  }
};
