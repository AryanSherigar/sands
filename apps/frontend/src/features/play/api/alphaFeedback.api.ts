import { apiClient } from "@/shared/lib/api-client";
import type {
  AlphaFeedbackRequest,
  AlphaFlagRequest,
} from "../types/alphaFeedback.types";

export const submitAlphaFeedback = async (
  request: AlphaFeedbackRequest,
): Promise<void> => {
  await apiClient.post("/v1/alpha/feedback", request);
};

export const flagAlphaNarration = async (
  turnId: string,
  request: AlphaFlagRequest,
): Promise<void> => {
  await apiClient.post(`/v1/alpha/turns/${turnId}/flag`, request);
};
