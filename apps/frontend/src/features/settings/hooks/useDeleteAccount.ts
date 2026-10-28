import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { reauthenticateWithPopup } from "firebase/auth";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { deleteMyAccount } from "@/shared/api/account.api";
import { auth, googleProvider } from "@/shared/lib/firebase";
import { logEvent } from "@/shared/lib/logger";
import { useToastStore } from "@/shared/stores/toast.store";
import {
  DELETE_FAILED_MESSAGE,
  DELETE_REQUESTED_MESSAGE,
  REAUTH_FAILED_MESSAGE,
} from "../constants/settings.constants";

export const useDeleteAccount = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const confirmDeletion = async (): Promise<void> => {
    setIsDeleting(true);
    setErrorMessage(null);
    if (!(await reauthenticate())) {
      setErrorMessage(REAUTH_FAILED_MESSAGE);
      setIsDeleting(false);
      return;
    }
    try {
      await deleteMyAccount();
    } catch (error: unknown) {
      logEvent("warning", "account_delete_failed", { error: String(error) });
      setErrorMessage(DELETE_FAILED_MESSAGE);
      setIsDeleting(false);
      return;
    }
    await logout();
    useToastStore.getState().showToast(DELETE_REQUESTED_MESSAGE, "info");
    navigate("/", { replace: true });
  };

  return { confirmDeletion, isDeleting, errorMessage };
};

async function reauthenticate(): Promise<boolean> {
  if (!auth.currentUser) return import.meta.env.DEV;
  try {
    await reauthenticateWithPopup(auth.currentUser, googleProvider);
    return true;
  } catch (error: unknown) {
    logEvent("warning", "account_delete_reauth_failed", { error: String(error) });
    return false;
  }
}
