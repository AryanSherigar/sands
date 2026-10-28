import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAlphaConfig } from "@/shared/hooks/useAlphaConfig";
import { useAlphaConsentStatus } from "@/shared/hooks/useAlphaConsentStatus";
import { useAuthStore } from "../../stores/auth.store";
import { AlphaReconsent } from "../AlphaReconsent/AlphaReconsent";

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();
  const { data: alphaConfig, isPending: isConfigPending } = useAlphaConfig();
  const isAlphaMode = alphaConfig?.is_alpha_mode ?? false;
  const consentStatus = useAlphaConsentStatus(isAuthenticated && isAlphaMode);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (isConfigPending || (isAlphaMode && consentStatus.isPending)) {
    return <div>Loading...</div>;
  }

  if (isAlphaMode && consentStatus.data?.alpha_consent_is_current === false) {
    return <AlphaReconsent version={alphaConfig?.consent_version ?? null} />;
  }

  return <>{children}</>;
};
