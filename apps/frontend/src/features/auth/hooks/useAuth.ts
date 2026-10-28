import { useState } from "react";
import axios from "axios";
import { signInWithPopup } from "firebase/auth";
import { auth, googleProvider } from "@/shared/lib/firebase";
import { useToastStore } from "@/shared/stores/toast.store";
import { fetchAlphaConfig } from "@/shared/api/alpha.api";
import {
  exchangeFirebaseToken,
  logoutUser,
  type AlphaTokenFields,
} from "../api/auth.api";
import { clearInvite, readInvite } from "../lib/inviteStorage";
import { useAuthStore } from "../stores/auth.store";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import {
  ALPHA_ERROR_MESSAGES,
  POPUP_CANCELLED_ERROR_CODES,
  SIGN_IN_CANCELLED_MESSAGE,
  SIGN_IN_FAILED_MESSAGE,
} from "../constants/auth-messages";

const getAlphaErrorMessage = (err: unknown): string | null => {
  if (!axios.isAxiosError(err) || err.response?.status !== 403) return null;
  const code: unknown = err.response.data?.code;
  return typeof code === "string" ? (ALPHA_ERROR_MESSAGES[code] ?? null) : null;
};

const getSignInErrorMessage = (err: unknown): string => {
  const alphaMessage = getAlphaErrorMessage(err);
  if (alphaMessage) return alphaMessage;
  const code =
    typeof err === "object" && err !== null && "code" in err
      ? String((err as { code: unknown }).code)
      : "";
  return POPUP_CANCELLED_ERROR_CODES.includes(code)
    ? SIGN_IN_CANCELLED_MESSAGE
    : SIGN_IN_FAILED_MESSAGE;
};

const loadAlphaTokenFields = async (): Promise<AlphaTokenFields | undefined> => {
  try {
    const config = await fetchAlphaConfig();
    if (!config.is_alpha_mode) return undefined;
    return {
      inviteCode: readInvite() ?? undefined,
      consentVersion: config.consent_version ?? undefined,
    };
  } catch {
    // NOTE: without the config the exchange goes out plain; in alpha mode the
    // server then refuses with a specific code the UI can explain.
    return undefined;
  }
};

const ACCOUNT_RESTORED_MESSAGE = "Welcome back, your account was restored.";

export const useAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    setAuth,
    logout: storeLogout,
  } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const loginWithGoogle = async (): Promise<boolean> => {
    setIsGoogleLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const idToken = await result.user.getIdToken();

      const { access_token, user: apiUser, is_account_restored } =
        await exchangeFirebaseToken(idToken, await loadAlphaTokenFields());
      clearInvite();
      setAuth(access_token, apiUser);
      setError(null);
      if (is_account_restored) {
        useToastStore
          .getState()
          .showToast(ACCOUNT_RESTORED_MESSAGE, "success");
      }
      return true;
    } catch (err: unknown) {
      setError(getSignInErrorMessage(err));
      return false;
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const loginAsDevUser = async () => {
    if (!import.meta.env.DEV) {
      setError("Dev login is unavailable in this environment.");
      return;
    }
    try {
      const { access_token, user: apiUser } =
        await exchangeFirebaseToken("mock-dev-token");
      setAuth(access_token, apiUser);
      setError(null);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Dev login failed"));
    }
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch {
      // NOTE: proceed with client-side logout even if the backend call
      // fails — a network error here shouldn't trap the user in a
      // logged-in UI state.
    }
    if (auth.currentUser) {
      await auth.signOut();
    }
    storeLogout();
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    isGoogleLoading,
    error,
    loginWithGoogle,
    loginAsDevUser,
    logout,
  };
};
