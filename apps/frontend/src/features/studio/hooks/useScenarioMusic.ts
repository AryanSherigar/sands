import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ScenarioMood } from "@/shared/types/audio.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import {
  listScenarioMusic,
  setDefaultMusicTrack,
  uploadMusicTrack,
} from "../api/music.api";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runChildWrite } from "../lib/childWrite";

export const useScenarioMusic = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const guardedWrite = <T,>(write: () => Promise<T>): Promise<T> =>
    runChildWrite(queryClient, requireScenarioId(scenarioId), write);
  const queryKey = ["scenario-music", scenarioId];
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
  };

  const musicQuery = useQuery({
    queryKey,
    queryFn: () => listScenarioMusic(scenarioId as string),
    enabled: Boolean(scenarioId),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ mood, file }: { mood: ScenarioMood; file: File }) =>
      guardedWrite(() => uploadMusicTrack(requireScenarioId(scenarioId), mood, file)),
    onSuccess: invalidate,
  });

  const setDefaultMutation = useMutation({
    mutationFn: (mood: ScenarioMood) =>
      guardedWrite(() => setDefaultMusicTrack(requireScenarioId(scenarioId), mood)),
    onSuccess: invalidate,
  });

  return {
    slots: musicQuery.data?.items ?? [],
    isLoading: musicQuery.isLoading,
    error: musicQuery.error,
    uploadTrack: uploadMutation.mutate,
    isUploading: uploadMutation.isPending,
    uploadError: uploadMutation.error
      ? extractErrorMessage(uploadMutation.error, "Failed to upload track.")
      : null,
    setDefaultTrack: setDefaultMutation.mutate,
    isSettingDefault: setDefaultMutation.isPending,
  };
};
