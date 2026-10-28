import { apiClient } from "@/shared/lib/api-client";
import type {
  OnboardingPayload,
  OnboardingProfileDraft,
  OnboardingResult,
} from "@/shared/types/onboarding.types";

export const completeOnboarding = async (
  payload: OnboardingPayload,
): Promise<OnboardingResult> => {
  const { data } = await apiClient.post<OnboardingResult>(
    "/v1/users/me/onboarding",
    payload,
  );
  return data;
};

export const redoOnboarding = async (
  payload: OnboardingPayload,
): Promise<OnboardingResult> => {
  const { data } = await apiClient.patch<OnboardingResult>(
    "/v1/users/me",
    payload,
  );
  return data;
};

export const fetchOnboardingProfileDraft =
  async (): Promise<OnboardingProfileDraft> => {
    const { data } = await apiClient.get<OnboardingProfileDraft>("/v1/users/me");
    return data;
  };
