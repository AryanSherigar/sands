/**
 * The only file that reads a streamed fetch response body for SSE — every
 * SSE consumer in the app routes through here.
 *
 * Both GET and POST connections use fetch()'s streaming body rather than the
 * browser's native EventSource: EventSource cannot send a custom
 * Authorization header, and this app's auth (both Core API and TRS) is
 * Bearer-JWT-based, not cookie-based, so EventSource can't authenticate to
 * the notifications endpoint. Using one mechanism for both GET and POST also
 * keeps this file's parsing logic single-sourced.
 */
import { parseAlphaPausedError } from "./alpha-paused-error";
import { REQUEST_ID_HEADER } from "./request-id";
import { refreshAuthToken } from "./api-client";
import { logEvent } from "./logger";
import {
  HTTP_SERVICE_UNAVAILABLE,
  HTTP_TOO_MANY_REQUESTS,
  RateLimitError,
  parseRateLimitError,
} from "./rate-limit-error";

export interface SSEHandlers {
  onEvent: (eventName: string, data: string) => void;
  onError?: (error: unknown) => void;
  onOpen?: () => void;
  // Fires when the underlying connection ends without a fetch/network
  // error — including a server-side stream that closes mid-generation
  // (e.g. an unhandled exception after headers were already sent, so it
  // never reaches onError). Callers that expect an explicit terminal event
  // of their own (like TRS's "done"/"degraded") should treat a close
  // without having seen one as a failure, not a silent success.
  onClose?: () => void;
}

export interface SSERetryConfig {
  initialDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
}

const DEFAULT_RETRY_CONFIG: SSERetryConfig = {
  initialDelayMs: 1000,
  maxDelayMs: 15000,
  backoffMultiplier: 1.5,
};

export class FantasyActionRefusedError extends Error {
  override name = "FantasyActionRefusedError";
}

function computeNextBackoff(
  currentDelay: number,
  config: SSERetryConfig,
): number {
  return Math.min(currentDelay * config.backoffMultiplier, config.maxDelayMs);
}

function createReconnectingHandlers(
  handlers: SSEHandlers,
  onResetDelay: () => void,
  onReconnect: () => void,
): SSEHandlers {
  return {
    ...handlers,
    onOpen: () => {
      onResetDelay();
      handlers.onOpen?.();
    },
    onClose: () => {
      handlers.onClose?.();
      onReconnect();
    },
    onError: (error: unknown) => {
      handlers.onError?.(error);
      onReconnect();
    },
  };
}

/** Persistent GET-based SSE connection (notifications, spectate streams). */
export function createGetSSEConnection(
  url: string,
  authToken: string | null,
  handlers: SSEHandlers,
  requestId?: string,
  retryConfig?: Partial<SSERetryConfig>,
): () => void {
  const config = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };
  const controller = new AbortController();
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let retryDelayMs = config.initialDelayMs;

  const reconnect = () => {
    if (controller.signal.aborted || retryTimer !== null) return;
    const currentDelay = retryDelayMs;
    retryDelayMs = computeNextBackoff(retryDelayMs, config);
    retryTimer = setTimeout(() => {
      retryTimer = null;
      connect();
    }, currentDelay);
  };

  const wrappedHandlers = createReconnectingHandlers(
    handlers,
    () => {
      retryDelayMs = config.initialDelayMs;
    },
    reconnect,
  );

  const connect = () => {
    if (controller.signal.aborted) return;
    void streamRequest(
      url,
      "GET",
      undefined,
      authToken,
      wrappedHandlers,
      controller.signal,
      requestId,
    );
  };

  connect();
  return () => {
    if (retryTimer !== null) clearTimeout(retryTimer);
    controller.abort();
  };
}

/** One-shot POST-then-stream SSE connection (TRS's POST /v1/turn). */
export function createPostSSEConnection(
  url: string,
  body: unknown,
  authToken: string | null,
  handlers: SSEHandlers,
  requestId?: string,
): () => void {
  return createFetchSSEConnection(
    url,
    "POST",
    body,
    authToken,
    handlers,
    requestId,
  );
}

function createFetchSSEConnection(
  url: string,
  method: "GET" | "POST",
  body: unknown,
  authToken: string | null,
  handlers: SSEHandlers,
  requestId?: string,
): () => void {
  const controller = new AbortController();
  void streamRequest(
    url,
    method,
    body,
    authToken,
    handlers,
    controller.signal,
    requestId,
  );
  return () => controller.abort();
}

// Mirrors shared/lib/api-client.ts's request interceptor: when there's no
// logged-in session, dev builds fall back to a fixed dev user id rather than
// going unauthenticated. Kept in sync with that file intentionally — SSE
// requests need the same fallback REST requests already get.
const DEV_USER_ID =
  import.meta.env.VITE_DEV_USER_ID || "464f4a91-86b5-47ce-b19a-19f37615230f";

/** Bearer token, else the dev-user fallback header — the one place this
 * app's TRS auth convention lives, reused by any direct TRS fetch caller
 * (not just SSE), such as features/play/api/voice.api.ts. */
export function buildTrsAuthHeaders(
  authToken: string | null,
): Record<string, string> {
  if (authToken) return { Authorization: `Bearer ${authToken}` };
  if (import.meta.env.DEV) return { "X-Dev-User-Id": DEV_USER_ID };
  return {};
}

/** Reads a fetch() response that already failed: a RateLimitError when it
 * is a rate-limit/quota refusal, else null. Shared with direct TRS fetch
 * callers such as features/play/api/voice.api.ts. */
export async function readRateLimitError(
  response: Response,
): Promise<RateLimitError | null> {
  const isLimitStatus =
    response.status === HTTP_TOO_MANY_REQUESTS ||
    response.status === HTTP_SERVICE_UNAVAILABLE;
  if (!isLimitStatus) return null;
  try {
    const body: unknown = await response.json();
    return parseRateLimitError(
      response.status,
      body,
      response.headers.get("Retry-After"),
    );
  } catch (error) {
    logEvent("warning", "rate_limit_body_unparseable", {
      status: response.status,
      message: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

async function buildServiceUnavailableError(response: Response): Promise<Error> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch (error) {
    logEvent("warning", "service_unavailable_body_unparseable", {
      message: error instanceof Error ? error.message : String(error),
    });
  }
  return (
    parseAlphaPausedError(response.status, body) ??
    parseRateLimitError(
      response.status,
      body,
      response.headers.get("Retry-After"),
    ) ??
    new Error(`SSE request failed: ${response.status}`)
  );
}

async function buildResponseError(response: Response): Promise<Error> {
  if (response.status === 409) {
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "code" in body && body.code === "fantasy_action_refused" && "detail" in body && typeof body.detail === "string") {
        return new FantasyActionRefusedError(body.detail);
      }
    } catch {
      // Other conflicts use the generic transport error.
    }
    return new Error(`SSE request failed: ${response.status}`);
  }
  if (response.status === HTTP_SERVICE_UNAVAILABLE) {
    return buildServiceUnavailableError(response);
  }
  const rateLimitError = await readRateLimitError(response);
  return rateLimitError ?? new Error(`SSE request failed: ${response.status}`);
}

function buildRequestIdHeader(requestId?: string): Record<string, string> {
  return requestId ? { [REQUEST_ID_HEADER]: requestId } : {};
}

async function streamRequest(
  url: string,
  method: "GET" | "POST",
  body: unknown,
  authToken: string | null,
  handlers: SSEHandlers,
  signal: AbortSignal,
  requestId?: string,
  hasRetriedAfterRefresh: boolean = false,
): Promise<void> {
  try {
    const response = await fetch(url, {
      method,
      headers: {
        ...(method === "POST" ? { "Content-Type": "application/json" } : {}),
        ...buildTrsAuthHeaders(authToken),
        ...buildRequestIdHeader(requestId),
      },
      body: method === "POST" ? JSON.stringify(body) : undefined,
      signal,
    });

    if (response.status === 401 && !hasRetriedAfterRefresh) {
      const refreshedToken = await refreshAuthToken();
      if (refreshedToken && !signal.aborted) {
        return streamRequest(
          url,
          method,
          body,
          refreshedToken,
          handlers,
          signal,
          requestId,
          true,
        );
      }
    }

    if (!response.ok || !response.body) {
      handlers.onError?.(await buildResponseError(response));
      return;
    }
    handlers.onOpen?.();
    await readEventStream(response.body, handlers);
    handlers.onClose?.();
  } catch (error) {
    if (signal.aborted) return;
    handlers.onError?.(error);
  }
}

async function readEventStream(
  body: ReadableStream<Uint8Array>,
  handlers: SSEHandlers,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let isStreaming = true;
  while (isStreaming) {
    const { done, value } = await reader.read();
    if (done) {
      isStreaming = false;
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    buffer = consumeSSEFrames(buffer, handlers);
  }
  if (buffer.length > 0) {
    consumeSSEFrames(buffer + "\n\n", handlers);
  }
}

/** Parses complete "event: x\ndata: y\n\n" blocks out of buffer, returning the remainder. */
function consumeSSEFrames(buffer: string, handlers: SSEHandlers): string {
  let content = buffer;
  let trailingReturn = "";
  if (content.endsWith("\r")) {
    content = content.slice(0, -1);
    trailingReturn = "\r";
  }

  const normalized = content.replace(/\r\n/g, "\n");
  const frames = normalized.split("\n\n");
  const remainder = frames.pop() ?? "";
  for (const frame of frames) {
    const { event, data } = parseSSEFrame(frame);
    if (event) handlers.onEvent(event, data);
  }
  return remainder + trailingReturn;
}

function parseSSEFrame(frame: string): { event: string | null; data: string } {
  let event: string | null = null;
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      const raw = line.slice(5);
      dataLines.push(raw.startsWith(" ") ? raw.slice(1) : raw);
    }
  }
  return { event, data: dataLines.join("\n") };
}
