import { useAuthStore } from "@/features/auth/stores/auth.store";
import { refreshAuthToken } from "@/shared/lib/api-client";
import {
  buildTrsAuthHeaders,
  readRateLimitError,
} from "@/shared/lib/sse-client";

const TRS_BASE_URL = import.meta.env.VITE_TRS_URL || "http://localhost:8001";
const HTTP_UNAUTHORIZED = 401;

export class MemoryRetryError extends Error {}

export interface MemoryRetryResponse {
  degraded_reasons: string[];
}

const postMemoryRetry = (
  playthroughId: string,
  accessToken: string | null,
): Promise<Response> =>
  fetch(`${TRS_BASE_URL}/v1/playthroughs/${playthroughId}/memory/retry`, {
    method: "POST",
    headers: buildTrsAuthHeaders(accessToken),
  });

const postWithOneRefresh = async (playthroughId: string): Promise<Response> => {
  const response = await postMemoryRetry(
    playthroughId,
    useAuthStore.getState().accessToken,
  );
  if (response.status !== HTTP_UNAUTHORIZED) return response;
  const refreshedToken = await refreshAuthToken();
  if (!refreshedToken) return response;
  return postMemoryRetry(playthroughId, refreshedToken);
};

/** Asks the server to retry delayed story memory. Never replays a turn. */
export async function retryMemory(
  playthroughId: string,
): Promise<MemoryRetryResponse> {
  const response = await postWithOneRefresh(playthroughId);

  if (!response.ok) {
    const rateLimitError = await readRateLimitError(response);
    if (rateLimitError) throw rateLimitError;
    throw new MemoryRetryError(`Memory retry failed: ${response.status}`);
  }
  return (await response.json()) as MemoryRetryResponse;
}
