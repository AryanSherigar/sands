import { apiClient } from "@/shared/lib/api-client";
import type {
  AlphaConfig,
  AlphaConsentStatus,
} from "@/shared/types/alpha.types";

export const fetchAlphaConfig = async (): Promise<AlphaConfig> => {
  const response = await apiClient.get<AlphaConfig>("/v1/alpha/config");
  return response.data;
};

export const fetchAlphaConsentStatus = async (): Promise<AlphaConsentStatus> => {
  const response = await apiClient.get<AlphaConsentStatus>("/v1/users/me");
  return response.data;
};

export const recordAlphaConsent = async (
  version: string,
): Promise<AlphaConsentStatus> => {
  const response = await apiClient.post<AlphaConsentStatus>(
    "/v1/users/me/alpha-consent",
    { version },
  );
  return response.data;
};
