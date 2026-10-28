import { useMutation, useQueryClient } from "@tanstack/react-query";
import { recordAlphaConsent } from "@/shared/api/alpha.api";
import { ALPHA_CONSENT_STATUS_QUERY_KEY } from "@/shared/hooks/useAlphaConsentStatus";

export function useRecordAlphaConsent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: recordAlphaConsent,
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ALPHA_CONSENT_STATUS_QUERY_KEY,
      }),
  });
}
