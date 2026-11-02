import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { generateClientActionId } from "@/shared/lib/request-id";
import { fetchCombatOptions, submitCombat } from "../api/combat.api";
import type { CombatCommand, CombatEvent, CombatState } from "../api/combat.api";
import type { PlaythroughData } from "../types/play.types";

export function useFantasyCombat(playthrough: PlaythroughData | null, isNarrating: boolean) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<CombatState | null>(null);
  const [event, setEvent] = useState<CombatEvent | null>(null);
  const [error, setError] = useState(false);
  const [isSubmitting, setSubmitting] = useState(false);
  const pending = useRef<CombatCommand | null>(null);
  const inFlight = useRef(false);
  const playthroughId = playthrough?.playthrough_id ?? "";
  const participantId = playthrough?.participant_id ?? "";
  const enabled = Boolean(playthrough?.combat_enabled && participantId && !playthrough?.is_spectator && !playthrough?.ended_outcome_tag);
  const key = ["combat-options", playthroughId, participantId] as const;
  const options = useQuery({ queryKey: key, queryFn: () => fetchCombatOptions(playthroughId, participantId), enabled, retry: false, staleTime: 0 });

  useEffect(() => {
    if (enabled && !isNarrating) void queryClient.invalidateQueries({ queryKey: ["combat-options", playthroughId, participantId] });
  }, [enabled, isNarrating, playthroughId, participantId, queryClient]);
  useEffect(() => { setState(null); setEvent(null); setError(false); pending.current = null; }, [playthroughId]);

  const combat = state ?? options.data?.state ?? null;
  const refreshPlaythrough = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["playthrough", playthroughId] }),
      queryClient.invalidateQueries({ queryKey: ["playthrough-turns", playthroughId] }),
    ]);
  };
  const execute = async (command: CombatCommand) => {
    if (inFlight.current) return;
    inFlight.current = true;
    pending.current = command;
    setSubmitting(true);
    setError(false);
    try {
      const result = await submitCombat(command);
      const next = "state" in result ? result.state : result;
      setState(next);
      setEvent("event" in result ? result.event ?? null : null);
      pending.current = null;
      await refreshPlaythrough();
      if (command.path === "outcome") {
        setState(null);
        await options.refetch();
      }
    } catch {
      setError(true);
    } finally {
      inFlight.current = false;
      setSubmitting(false);
    }
  };
  const common = { playthrough_id: playthroughId, participant_id: participantId };
  const start = (encounterId: string) => void execute({ path: "start", body: { ...common, encounter_id: encounterId, client_action_id: generateClientActionId() } });
  const attack = () => {
    const action = combat?.legal_actions[0];
    if (!action || !combat) return;
    void execute({ path: "action", body: { ...common, action: { ...action, expected_revision: combat.revision, client_action_id: generateClientActionId() } } });
  };
  const resolve = () => {
    if (combat) void execute({ path: "outcome", body: { ...common, expected_revision: combat.revision, client_action_id: generateClientActionId() } });
  };
  const retry = () => { if (pending.current) void execute(pending.current); };
  const refresh = async () => { pending.current = null; setState(null); setError(false); await options.refetch(); await refreshPlaythrough(); };
  const dismiss = async () => { setState(null); setEvent(null); await options.refetch(); };

  return { enabled, combat, encounters: options.data?.encounters ?? [], event, error, isSubmitting,
    isLoading: enabled && options.isLoading, isLoadError: enabled && options.isError,
    isBlocked: enabled && (options.isLoading || options.isError || isSubmitting || error || Boolean(combat)),
    start, attack, resolve, retry, refresh, dismiss };
}
