import axios from "axios";
import { apiClient } from "@/shared/lib/api-client";
import { TokenResponse } from "../types/auth.types";

export interface AlphaTokenFields {
  inviteCode?: string;
  consentVersion?: string;
}

export const exchangeFirebaseToken = async (
  firebaseIdToken: string,
  alpha?: AlphaTokenFields,
): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>("/v1/auth/token", {
    firebase_id_token: firebaseIdToken,
    ...(alpha?.inviteCode && { invite_code: alpha.inviteCode }),
    ...(alpha?.consentVersion && {
      alpha_consent_version: alpha.consentVersion,
    }),
  });
  return response.data;
};

// Refresh tokens rotate server-side on every use (the old jti is invalidated
// the instant a new one is issued), so two independent callers racing to
// refresh — AuthProvider's boot-time call and api-client's 401 interceptor
// both call this — send the same pre-rotation cookie and the loser gets
// rejected as "already used or rotated". Single-flighting collapses any
// concurrent callers within this tab onto one request/response instead of
// two, which is what the server-side rotation assumes.
let inFlightRefresh: Promise<TokenResponse> | null = null;

const STALE_REFRESH_RETRY_DELAY_MS = 300;

// Module state is per-tab, so this guard can't stop a *different* tab from
// racing the same rotation: two tabs open at once both hold the
// pre-rotation cookie, both hit the 15-minute access-token expiry around
// the same moment, and the losing tab's request is rejected as stale even
// though it did nothing wrong. By the time that rejection arrives, the
// browser's cookie jar already holds the winning tab's newly-rotated
// cookie (cookies are shared across tabs of the same origin) — one retry
// after a short delay picks it up instead of forcing that tab to log out.
function isStaleRefreshTokenError(error: unknown): boolean {
  return (
    axios.isAxiosError(error) &&
    error.response?.status === 401 &&
    error.response?.data?.detail === "Refresh token already used or rotated"
  );
}

const performRefresh = async (): Promise<TokenResponse> => {
  try {
    const response = await apiClient.post<TokenResponse>("/v1/auth/refresh");
    return response.data;
  } catch (error) {
    if (!isStaleRefreshTokenError(error)) throw error;
    await new Promise((resolve) =>
      setTimeout(resolve, STALE_REFRESH_RETRY_DELAY_MS),
    );
    const retryResponse =
      await apiClient.post<TokenResponse>("/v1/auth/refresh");
    return retryResponse.data;
  }
};

export const refreshAccessToken = async (): Promise<TokenResponse> => {
  if (inFlightRefresh) return inFlightRefresh;
  inFlightRefresh = performRefresh().finally(() => {
    inFlightRefresh = null;
  });
  return inFlightRefresh;
};

export const logoutUser = async (): Promise<void> => {
  await apiClient.post("/v1/auth/logout");
};
