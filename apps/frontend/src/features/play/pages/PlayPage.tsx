import { useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { MapViewer } from "../components/MapViewer/MapViewer";
import { MinigameOverlay } from "../components/MinigameOverlay/MinigameOverlay";
import { CheckPromptOverlay } from "../components/CheckPromptOverlay/CheckPromptOverlay";
import { RuleCheckOverlay } from "../components/RuleCheckOverlay/RuleCheckOverlay";
import { TensionTap } from "../components/PlayScreen/TensionTap/TensionTap";
import { PlayScreen } from "../components/PlayScreen/PlayScreen";
import { usePlayStore } from "../stores/play.store";
import { usePlaythrough } from "../hooks/usePlaythrough";
import { usePlaythroughTurns } from "../hooks/useTurns";
import { useNotifications } from "../hooks/useNotifications";
import { usePhantomAudio } from "../hooks/usePhantomAudio";
import { useTierAudio } from "../hooks/useTierAudio";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import {
  buildMasterPlaythroughData,
  buildNewbiePlaythroughData,
  buildStrategyPlaythroughData,
} from "./playthroughDataBuilders";
import { shouldApplyServerPlaythrough } from "./shouldApplyServerPlaythrough";

export function PlayPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const setPlaythrough = usePlayStore((s) => s.setPlaythrough);
  const queryClient = useQueryClient();

  const { data: serverPlaythrough, isLoading, isError } = usePlaythrough(id);
  const { data: turnsData } = usePlaythroughTurns(id);

  const isSpectatorMode = searchParams.get("mode") === "spectate";
  const isMultiplayer = (serverPlaythrough?.participants.length ?? 0) > 1;

  const { isMyTurnSignal, acknowledgeMyTurn } = useNotifications(
    id ?? null,
    serverPlaythrough?.participant_id ?? null,
    isMultiplayer && !isSpectatorMode,
  );

  useEffect(() => {
    if (!isMyTurnSignal || !id) return;
    void queryClient.invalidateQueries({ queryKey: ["playthrough", id] });
    acknowledgeMyTurn();
  }, [isMyTurnSignal, id, queryClient, acknowledgeMyTurn]);

  useTierAudio();
  usePhantomAudio();

  useEffect(() => {
    return () => {
      ambientSoundtrack.stop();
    };
  }, []);

  useEffect(() => {
    if (!serverPlaythrough) return;

    const mode =
      (serverPlaythrough.scenario_snapshot?.mode as
        | "newbie"
        | "master"
        | "strategy") ||
      "newbie";
    let playthroughData;
    if (mode === "master") {
      playthroughData = buildMasterPlaythroughData(
        serverPlaythrough,
        turnsData,
        isSpectatorMode,
      );
    } else if (mode === "strategy") {
      playthroughData = buildStrategyPlaythroughData(
        serverPlaythrough,
        turnsData,
        isSpectatorMode,
      );
    } else {
      playthroughData = buildNewbiePlaythroughData(
        serverPlaythrough,
        turnsData,
        isSpectatorMode,
      );
    }

    const current = usePlayStore.getState().playthrough;
    if (!shouldApplyServerPlaythrough(current, playthroughData)) return;

    setPlaythrough(playthroughData);
  }, [serverPlaythrough, turnsData, isSpectatorMode, setPlaythrough]);

  if (id && isLoading) {
    return (
      <div className="min-h-dvh w-full bg-surface-sunken flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
        <p className="font-mono text-xs text-content-muted tracking-widest uppercase">
          LOADING PLAYTHROUGH SESSION...
        </p>
      </div>
    );
  }

  if (id && isError) {
    return (
      <div className="min-h-dvh w-full bg-surface-sunken text-content flex flex-col items-center justify-center p-6 text-center space-y-4">
        <h1 className="font-display text-2xl text-danger font-semibold">
          Failed to Load Playthrough
        </h1>
        <p className="font-mono text-xs text-content-muted max-w-sm">
          The requested playthrough session could not be retrieved from the
          server.
        </p>
      </div>
    );
  }

  return (
    <>
      <PlayScreen />
      <MapViewer
        scenarioSnapshot={serverPlaythrough?.scenario_snapshot}
        state={serverPlaythrough?.state}
      />
      <MinigameOverlay />
      <CheckPromptOverlay />
      <RuleCheckOverlay />
      <TensionTap />
    </>
  );
}
