import { useCallback, useEffect, useRef, useState } from "react";
import { createPostSSEConnection } from "@/shared/lib/sse-client";
import { logEvent } from "@/shared/lib/logger";
import { isRateLimitError } from "@/shared/lib/rate-limit-error";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { SCOPED_CHAT_WELCOME } from "../constants/scopedChat";
import { EMPTY_SCOPED_CONTEXT, toScopedRequestContext } from "../lib/scopedChat";
import { AssistantMessage, BlockValidation } from "../types/assistant.types";
import type { ScopedChatContext } from "../types/scopedChat.types";
import { useEntities } from "./useEntities";
import { useFacts } from "./useFacts";
import { useScenario } from "./useScenario";
import { useConditions } from "./useConditions";
import { useInvariants } from "./useInvariants";
import { useEndConditions } from "./useEndConditions";

export type AssistantChatMode = "master" | "scoped";

const TRS_BASE_URL = import.meta.env.VITE_TRS_URL || "http://localhost:8001";

/** Scoped by user_id so a different account on the same browser never sees
 * another creator's chat, and by scenario_id (falling back to "draft" before
 * the story is saved) so distinct scenarios never share one bucket. Returns null
 * — meaning "don't persist" — when there's no signed-in user yet, since an
 * unscoped key would itself be the kind of cross-user leak this guards against. */
const buildStorageKey = (
  mode: AssistantChatMode,
  userId: string | null,
  scenarioId?: string | null,
): string | null => {
  if (!userId) return null;
  const scenarioPart = scenarioId || "draft";
  return `sands_studio_assistant_chat:${mode}:${userId}:${scenarioPart}`;
};

const WELCOME_BY_MODE: Record<AssistantChatMode, string> = {
  master:
    "Greetings, creator. I am your systems co-designer. Tell me about the people, places, facts, or tracked values you want in this scenario, and I'll propose ready-to-apply pieces.",
  scoped: SCOPED_CHAT_WELCOME,
};

const buildWelcome = (mode: AssistantChatMode): AssistantMessage => ({
  id: "welcome",
  role: "assistant",
  content: WELCOME_BY_MODE[mode],
  timestamp: Date.now(),
});

const loadInitialMessages = (
  storageKey: string | null,
  mode: AssistantChatMode,
): AssistantMessage[] => {
  if (!storageKey) return [buildWelcome(mode)];
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) return [buildWelcome(mode)];
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) && parsed.length > 0
      ? parsed
      : [buildWelcome(mode)];
  } catch (error) {
    logEvent("warning", "assistant_chat_load_failed", {
      storage_key: storageKey,
      message: error instanceof Error ? error.message : String(error),
    });
    return [buildWelcome(mode)];
  }
};

export const useAssistantChat = (
  activeSection: string = "meta",
  mode: AssistantChatMode = "master",
  scenarioId: string | null = null,
  scopedContext: ScopedChatContext | null = null,
) => {
  const accessToken = useAuthStore((s) => s.accessToken);
  const userId = useAuthStore((s) => s.user?.user_id ?? null);
  const storageKey = buildStorageKey(mode, userId, scenarioId);
  const [messages, setMessages] = useState<AssistantMessage[]>(() =>
    loadInitialMessages(storageKey, mode),
  );
  const [isStreaming, setIsStreaming] = useState(false);
  const cancelStreamRef = useRef<(() => void) | null>(null);
  const { entities } = useEntities(mode === "master" ? scenarioId : null);
  const { facts } = useFacts(mode === "master" ? scenarioId : null);
  const { scenario } = useScenario(mode === "master" ? scenarioId : null);
  const { conditions } = useConditions(mode === "master" ? scenarioId : null);
  const { invariants } = useInvariants(mode === "master" ? scenarioId : null);
  const { endConditions } = useEndConditions(
    mode === "master" ? scenarioId : null,
  );
  const [blockValidationByMessage, setBlockValidationByMessage] = useState<
    Record<string, BlockValidation[]>
  >({});

  const previousStorageKeyRef = useRef(storageKey);
  useEffect(() => {
    if (previousStorageKeyRef.current === storageKey) return;
    previousStorageKeyRef.current = storageKey;
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setMessages(loadInitialMessages(storageKey, mode));
    setIsStreaming(false);
  }, [storageKey, mode]);

  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(messages));
    } catch (error) {
      logEvent("warning", "assistant_chat_persist_failed", {
        storage_key: storageKey,
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, [messages, storageKey]);

  const clearChat = useCallback(() => {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setMessages([buildWelcome(mode)]);
    setIsStreaming(false);
    if (storageKey) localStorage.removeItem(storageKey);
  }, [mode, storageKey]);

  const reportApplyError = useCallback((errorMessage: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `assistant-error-${Date.now()}`,
        role: "assistant",
        content: `⚠️ ${errorMessage}`,
        timestamp: Date.now(),
      },
    ]);
  }, []);

  const stopGeneration = useCallback(() => {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const buildMasterContext = useCallback(
    () => ({
      title: scenario?.title || "",
      logline: scenario?.logline || "",
      narrator_persona: scenario?.narrator_persona || "",
      opening_scene: scenario?.opening_scene || "",
      state_schema: scenario?.state_schema || {},
      entities: entities.map((e) => ({
        entity_id: e.entity_id,
        entity_type: e.entity_type,
        canonical_name: e.canonical_name,
        description: e.description || undefined,
        attributes_schema: e.attributes_schema,
      })),
      facts: facts.map((f) => ({
        fact_id: f.fact_id,
        subject_entity_id: f.subject_entity_id,
        predicate: f.predicate,
        object_entity_id: f.object_entity_id,
        object_literal: f.object_literal,
      })),
      conditions: conditions.map((c) => ({
        condition_id: c.condition_id,
        label: c.label,
      })),
      invariants: invariants.map((i) => ({
        invariant_id: i.invariant_id,
        label: i.label,
      })),
      end_conditions: endConditions.map((e) => ({
        end_condition_id: e.end_condition_id,
        outcome_tag: e.outcome_tag,
        outcome_title: e.outcome_title,
      })),
      active_tab: activeSection,
    }),
    [
      scenario,
      entities,
      facts,
      conditions,
      invariants,
      endConditions,
      activeSection,
    ],
  );

  const buildPayload = useCallback(
    (nextMessages: AssistantMessage[]) => {
      const base = {
        messages: nextMessages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        mode,
      };
      if (mode === "scoped") {
        return {
          ...base,
          scoped_context: toScopedRequestContext(scopedContext ?? EMPTY_SCOPED_CONTEXT),
        };
      }
      return { ...base, master_context: buildMasterContext() };
    },
    [mode, buildMasterContext, scopedContext],
  );

  const sendMessage = useCallback(
    (promptText: string) => {
      const trimmed = promptText.trim();
      if (!trimmed || isStreaming) return;

      const userMsg: AssistantMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        timestamp: Date.now(),
      };
      const assistantId = `assistant-${Date.now()}`;
      const placeholderAssistant: AssistantMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
      };

      const updatedHistory = [...messages, userMsg];
      setMessages([...updatedHistory, placeholderAssistant]);
      setIsStreaming(true);

      const url = `${TRS_BASE_URL}/v1/studio/assistant`;
      const payload = buildPayload(updatedHistory);

      const cancelFn = createPostSSEConnection(url, payload, accessToken, {
        onEvent: (event, data) => {
          if (event === "chunk") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: msg.content + data }
                  : msg,
              ),
            );
          } else if (event === "done") {
            setIsStreaming(false);
            if (data) {
              try {
                const parsed = JSON.parse(data);
                if (Array.isArray(parsed.block_validation)) {
                  setBlockValidationByMessage((prev) => ({
                    ...prev,
                    [assistantId]: parsed.block_validation,
                  }));
                }
              } catch (error) {
                logEvent("warning", "assistant_chat_done_payload_unparseable", {
                  message:
                    error instanceof Error ? error.message : String(error),
                });
              }
            }
          } else if (event === "error") {
            setIsStreaming(false);
            let errorText = "AI assistant is temporarily unavailable.";
            try {
              const parsed = JSON.parse(data);
              if (parsed.detail) errorText = parsed.detail;
            } catch (error) {
              logEvent("warning", "assistant_chat_error_payload_unparseable", {
                message:
                  error instanceof Error ? error.message : String(error),
              });
              if (data) errorText = data;
            }
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: `⚠️ ${errorText}` }
                  : msg,
              ),
            );
          }
        },
        onError: (error: unknown) => {
          setIsStreaming(false);
          const errorText = isRateLimitError(error)
            ? error.message
            : "Connection error. Please ensure the backend service is running and try again.";
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId && msg.content === ""
                ? { ...msg, content: `⚠️ ${errorText}` }
                : msg,
            ),
          );
        },
        onClose: () => {
          setIsStreaming(false);
        },
      });

      cancelStreamRef.current = cancelFn;
    },
    [messages, isStreaming, accessToken, buildPayload],
  );

  return {
    messages,
    isStreaming,
    sendMessage,
    clearChat,
    stopGeneration,
    reportApplyError,
    blockValidationByMessage,
  };
};
