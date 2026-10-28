import { isAxiosError } from "axios";

export const getErrorStatus = (error: unknown): number | null => {
  if (error === null || error === undefined) return null;
  if (isAxiosError(error)) return error.response?.status ?? null;
  return null;
};
