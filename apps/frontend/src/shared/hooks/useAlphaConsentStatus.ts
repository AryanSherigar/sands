import { useQuery } from "@tanstack/react-query";
import { fetchAlphaConsentStatus } from "../api/alpha.api";

export const ALPHA_CONSENT_STATUS_QUERY_KEY = ["alpha-consent-status"];

export function useAlphaConsentStatus(isEnabled: boolean) {
  return useQuery({
    queryKey: ALPHA_CONSENT_STATUS_QUERY_KEY,
    queryFn: fetchAlphaConsentStatus,
    enabled: isEnabled,
    staleTime: 0,
  });
}
