import { useEffect } from "react";
import { setAlphaCollectionEnabled } from "@/shared/lib/alpha-events";
import { useAlphaConsentStatus } from "./useAlphaConsentStatus";
import { useIsAlphaMode } from "./useIsAlphaMode";
import { useIsAuthenticated } from "./useIsAuthenticated";

export function useAlphaCollection(): boolean {
  const isAlphaMode = useIsAlphaMode();
  const isAuthenticated = useIsAuthenticated();
  const { data } = useAlphaConsentStatus(isAlphaMode && isAuthenticated);
  const isCollecting =
    isAlphaMode && isAuthenticated && data?.alpha_consent_is_current === true;

  useEffect(() => {
    setAlphaCollectionEnabled(isCollecting);
    return () => setAlphaCollectionEnabled(false);
  }, [isCollecting]);

  return isCollecting;
}
