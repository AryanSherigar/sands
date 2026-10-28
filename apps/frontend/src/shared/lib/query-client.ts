import { QueryClient } from "@tanstack/react-query";
import { isRateLimitError } from "./rate-limit-error";

const MAX_QUERY_RETRIES = 1;

/** A rate-limited request is never retried: a retry only spends more of the
 * same budget and prolongs the lockout. */
export const shouldRetryQuery = (
  failureCount: number,
  error: unknown,
): boolean => !isRateLimitError(error) && failureCount < MAX_QUERY_RETRIES;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      refetchOnWindowFocus: false,
      retry: shouldRetryQuery,
    },
  },
});
