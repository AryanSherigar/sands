import { useCallback, useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { createPostSSEConnection, type SSEHandlers } from "../lib/sse-client";

export type PostSSEStatus = "idle" | "connecting" | "open" | "closed";

export function usePostSSE(handlers: SSEHandlers) {
  const [status, setStatus] = useState<PostSSEStatus>("idle");
  const handlersRef = useRef(handlers);
  const disconnectRef = useRef<(() => void) | null>(null);
  const accessToken = useAuthStore((state) => state.accessToken);
  handlersRef.current = handlers;

  const stop = useCallback(() => {
    disconnectRef.current?.();
    disconnectRef.current = null;
  }, []);

  const start = useCallback(
    (url: string, body: unknown) => {
      stop();
      setStatus("connecting");
      disconnectRef.current = createPostSSEConnection(url, body, accessToken, {
        onEvent: (name, data) => handlersRef.current.onEvent(name, data),
        onOpen: () => {
          setStatus("open");
          handlersRef.current.onOpen?.();
        },
        onError: (error) => {
          setStatus("closed");
          handlersRef.current.onError?.(error);
        },
        onClose: () => {
          setStatus("closed");
          handlersRef.current.onClose?.();
        },
      });
    },
    [accessToken, stop],
  );

  useEffect(() => stop, [stop]);
  return { status, start, stop };
}
