import { useState } from "react";
import {
  signInWithEmailAndPassword,
  signInWithPopup,
  type User as FirebaseUser,
} from "firebase/auth";
import { auth, googleProvider } from "@/shared/lib/firebase";
import { useToastStore } from "@/shared/stores/toast.store";
import { exchangeFirebaseToken, logoutUser } from "../api/auth.api";
import { useAuthStore } from "../stores/auth.store";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import {
  EMAIL_INVALID_CREDENTIAL_ERROR_CODES,
  EMAIL_SIGN_IN_INVALID_MESSAGE,
  POPUP_CANCELLED_ERROR_CODES,
  SIGN_IN_CANCELLED_MESSAGE,
  SIGN_IN_FAILED_MESSAGE,
} from "../constants/auth-messages";

const getErrorCode = (err: unknown): string =>
  typeof err === "object" && err !== null && "code" in err
    ? String((err as { code: unknown }).code)
    : "";

const getEmailSignInErrorMessage = (err: unknown): string =>
  EMAIL_INVALID_CREDENTIAL_ERROR_CODES.includes(getErrorCode(err))
    ? EMAIL_SIGN_IN_INVALID_MESSAGE
    : SIGN_IN_FAILED_MESSAGE;

const getSignInErrorMessage = (err: unknown): string => {
  const code = getErrorCode(err);
  return POPUP_CANCELLED_ERROR_CODES.includes(code)
    ? SIGN_IN_CANCELLED_MESSAGE
    : SIGN_IN_FAILED_MESSAGE;
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
  const [emailError, setEmailError] = useState<string | null>(null);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);

  const completeSignIn = async (firebaseUser: FirebaseUser): Promise<void> => {
    const idToken = await firebaseUser.getIdToken();
    const { access_token, user: apiUser, is_account_restored } =
      await exchangeFirebaseToken(idToken);
    setAuth(access_token, apiUser);
    if (is_account_restored) {
      useToastStore.getState().showToast(ACCOUNT_RESTORED_MESSAGE, "success");
    }
  };

  const loginWithEmail = async (
    email: string,
    password: string,
  ): Promise<boolean> => {
    setIsEmailLoading(true);
    try {
      const result = await signInWithEmailAndPassword(auth, email, password);
      await completeSignIn(result.user);
      setEmailError(null);
      return true;
    } catch (err: unknown) {
      setEmailError(getEmailSignInErrorMessage(err));
      return false;
    } finally {
      setIsEmailLoading(false);
    }
  };

  const loginWithGoogle = async (): Promise<boolean> => {
    setIsGoogleLoading(true);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      await completeSignIn(result.user);
      setError(null);
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
    isEmailLoading,
    error,
    emailError,
    loginWithGoogle,
    loginWithEmail,
    loginAsDevUser,
    logout,
  };
};
