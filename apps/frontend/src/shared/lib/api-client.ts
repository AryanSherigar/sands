import axios from "axios";
import { REQUEST_ID_HEADER, generateRequestId } from "./request-id";
import { parseRateLimitError } from "./rate-limit-error";

export interface ApiClientAuthProvider {
  getAccessToken: () => string | null;
  refreshAccessToken: () => Promise<{ access_token: string; user: unknown }>;
  onAuthRefreshed: (token: string, user: unknown) => void;
  onAuthFailed: () => void;
}

let authProvider: ApiClientAuthProvider | null = null;

export const setupApiClientAuth = (provider: ApiClientAuthProvider): void => {
  authProvider = provider;
};

/** For callers that cannot go through the axios interceptors (keepalive
 * fetch on page hide). */
export const getApiAccessToken = (): string | null =>
  authProvider?.getAccessToken() ?? null;

const serializeParams = (params: Record<string, unknown>): string => {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      value.forEach((item) => searchParams.append(key, String(item)));
    } else {
      searchParams.append(key, String(value));
    }
  }
  return searchParams.toString();
};

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_CORE_API_URL || "http://localhost:8000",
  withCredentials: true,
  timeout: 8000,
  headers: {
    "Content-Type": "application/json",
  },
  paramsSerializer: serializeParams,
});

interface QueuedRequest {
  resolve: (token: string | null) => void;
  reject: (error: unknown) => void;
}

let isRefreshing = false;
let failedQueue: QueuedRequest[] = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.request.use(
  (config) => {
    const token = authProvider?.getAccessToken();
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    } else if (import.meta.env.DEV) {
      const devUserId =
        import.meta.env.VITE_DEV_USER_ID ||
        "464f4a91-86b5-47ce-b19a-19f37615230f";
      config.headers["X-Dev-User-Id"] = devUserId;
    }
    if (!config.headers[REQUEST_ID_HEADER]) {
      config.headers[REQUEST_ID_HEADER] = generateRequestId();
    }
    return config;
  },
  (error) => Promise.reject(error),
);

let ssePendingRefresh: Promise<string | null> | null = null;

/** Single-flight token refresh for sse-client.ts, which can't go through
 * axios interceptors since it reads a streamed fetch() response directly. */
export const refreshAuthToken = (): Promise<string | null> => {
  if (!authProvider) return Promise.resolve(null);
  if (!ssePendingRefresh) {
    ssePendingRefresh = authProvider
      .refreshAccessToken()
      .then(({ access_token, user }) => {
        authProvider?.onAuthRefreshed(access_token, user);
        return access_token;
      })
      .catch(() => {
        authProvider?.onAuthFailed();
        return null;
      })
      .finally(() => {
        ssePendingRefresh = null;
      });
  }
  return ssePendingRefresh;
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const response = error.response;
    const rateLimitError = response
      ? parseRateLimitError(
          response.status,
          response.data,
          response.headers?.["retry-after"],
        )
      : null;
    if (rateLimitError) return Promise.reject(rateLimitError);

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      originalRequest.url !== "/v1/auth/refresh"
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers["Authorization"] = "Bearer " + token;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      if (!authProvider) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { access_token, user } = await authProvider.refreshAccessToken();

        authProvider.onAuthRefreshed(access_token, user);

        processQueue(null, access_token);
        originalRequest.headers["Authorization"] = "Bearer " + access_token;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        authProvider.onAuthFailed();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  },
);
