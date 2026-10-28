import { apiClient } from "@/shared/lib/api-client";
import {
  AccountSummary,
  MaturePreference,
  VoiceOutputPreference,
} from "../types/userPreferences.types";

export const fetchVoiceOutputPreference =
  async (): Promise<VoiceOutputPreference> => {
    const { data } = await apiClient.get<VoiceOutputPreference>(
      "/v1/users/me",
    );
    return data;
  };

export const updateVoiceOutputPreference = async (
  enabled: boolean,
): Promise<VoiceOutputPreference> => {
  const { data } = await apiClient.patch<VoiceOutputPreference>(
    "/v1/users/me",
    { voice_output_enabled: enabled },
  );
  return data;
};

export const updateMaturePreference = async (
  isEnabled: boolean,
): Promise<MaturePreference> => {
  const { data } = await apiClient.patch<MaturePreference>("/v1/users/me", {
    show_mature: isEnabled,
  });
  return data;
};

export const fetchAccountSummary = async (): Promise<AccountSummary> => {
  const { data } = await apiClient.get<AccountSummary>("/v1/users/me");
  return data;
};
