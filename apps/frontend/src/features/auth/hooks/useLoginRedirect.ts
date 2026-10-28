import { useEffect } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { buildWelcomeHref } from "@/shared/lib/onboarding-routes";
import { useAuthStore } from "../stores/auth.store";

const HOME_PATH = "/";
const INITIAL_LOCATION_KEY = "default";

interface LocationFromState {
  pathname: string;
  search: string;
}

const resolveExplicitTarget = (
  fromState: LocationFromState | undefined,
  redirectParam: string | null,
): string | null => {
  if (fromState) return `${fromState.pathname}${fromState.search}`;
  if (redirectParam) return decodeURIComponent(redirectParam);
  return null;
};

export const useLoginRedirect = (): void => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const shouldOnboard = useAuthStore(
    (state) => state.user?.onboarding_completed === false,
  );
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const explicitTarget = resolveExplicitTarget(
    location.state?.from,
    searchParams.get("redirect"),
  );
  const canGoBack = location.key !== INITIAL_LOCATION_KEY;

  useEffect(() => {
    if (!isAuthenticated) return;
    if (shouldOnboard) {
      navigate(buildWelcomeHref(explicitTarget ?? HOME_PATH), { replace: true });
    } else if (explicitTarget) {
      navigate(explicitTarget, { replace: true });
    } else if (canGoBack) {
      navigate(-1);
    } else {
      navigate(HOME_PATH, { replace: true });
    }
  }, [isAuthenticated, shouldOnboard, explicitTarget, canGoBack, navigate]);
};
