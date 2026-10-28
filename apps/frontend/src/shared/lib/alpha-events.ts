/**
 * Queue and batch sender for the closed-alpha client events.
 *
 * A plain module, not server state. It never throws and never blocks
 * gameplay: when the endpoint fails the batch is dropped after one attempt.
 * Event names and props mirror core-api's closed registry
 * (app/models/alpha_event_props.py); nothing free-text may be passed in.
 */
import { apiClient, getApiAccessToken } from "./api-client";
import {
  ALPHA_EVENTS_ENDPOINT,
  ALPHA_EVENTS_FAILURE_WARNING,
  ALPHA_EVENTS_FLUSH_INTERVAL_MS,
  ALPHA_EVENTS_MAX_BATCH,
  ALPHA_EVENTS_MAX_QUEUE,
} from "@/shared/constants/alpha-events";
import type {
  AlphaEventName,
  AlphaEventPropsMap,
  EmitOptions,
  QueuedAlphaEvent,
} from "@/shared/types/alphaEvents.types";

const sessionId = crypto.randomUUID();
let isCollecting = false;
let queue: QueuedAlphaEvent[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let hasWarned = false;

export function setAlphaCollectionEnabled(isEnabled: boolean): void {
  isCollecting = isEnabled;
  if (!isEnabled) discardQueue();
}

export function emitAlphaEvent<Name extends AlphaEventName>(
  name: Name,
  props: AlphaEventPropsMap[Name],
  options: EmitOptions = {},
): void {
  if (!isCollecting) return;
  queue.push({
    name,
    client_ts: new Date().toISOString(),
    playthrough_id: options.playthroughId,
    props: { ...props },
  });
  if (queue.length > ALPHA_EVENTS_MAX_QUEUE) queue.shift();
  if (queue.length >= ALPHA_EVENTS_MAX_BATCH) {
    void flushAlphaEvents();
    return;
  }
  scheduleFlush();
}

export async function flushAlphaEvents(): Promise<void> {
  const batch = takeBatch();
  if (batch.length === 0) return;
  try {
    await apiClient.post(ALPHA_EVENTS_ENDPOINT, {
      session_id: sessionId,
      events: batch,
    });
  } catch {
    warnOnce();
  }
}

export function flushAlphaEventsOnHide(): void {
  let batch = takeBatch();
  while (batch.length > 0) {
    sendWithKeepalive(batch);
    batch = takeBatch();
  }
}

function sendWithKeepalive(batch: QueuedAlphaEvent[]): void {
  const token = getApiAccessToken();
  const baseURL = apiClient.defaults.baseURL ?? "";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    void fetch(`${baseURL}${ALPHA_EVENTS_ENDPOINT}`, {
      method: "POST",
      headers,
      body: JSON.stringify({ session_id: sessionId, events: batch }),
      keepalive: true,
    }).catch(warnOnce);
  } catch {
    warnOnce();
  }
}

export function resetAlphaEventsForTests(): void {
  isCollecting = false;
  hasWarned = false;
  discardQueue();
}

function takeBatch(): QueuedAlphaEvent[] {
  clearFlushTimer();
  const batch = queue.slice(0, ALPHA_EVENTS_MAX_BATCH);
  queue = queue.slice(ALPHA_EVENTS_MAX_BATCH);
  if (queue.length > 0) scheduleFlush();
  return batch;
}

function scheduleFlush(): void {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    void flushAlphaEvents();
  }, ALPHA_EVENTS_FLUSH_INTERVAL_MS);
}

function clearFlushTimer(): void {
  if (!flushTimer) return;
  clearTimeout(flushTimer);
  flushTimer = null;
}

function discardQueue(): void {
  queue = [];
  clearFlushTimer();
}

function warnOnce(): void {
  if (hasWarned) return;
  hasWarned = true;
  console.warn(ALPHA_EVENTS_FAILURE_WARNING);
}
