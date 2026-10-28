import axios from "axios";
import { useAuthStore } from "../stores/auth.store";

const HTTP_FORBIDDEN = 403;
const ACCOUNT_SUSPENDED_CODE = "account_suspended";

export const isAccountSuspendedError = (error: unknown): boolean =>
  axios.isAxiosError(error) &&
  error.response?.status === HTTP_FORBIDDEN &&
  error.response.data?.code === ACCOUNT_SUSPENDED_CODE;

/** Records a suspension so the sign-in page can explain it; true when it was one. */
export const markSuspendedIfRefused = (error: unknown): boolean => {
  if (!isAccountSuspendedError(error)) return false;
  useAuthStore.getState().markSuspended();
  return true;
};
