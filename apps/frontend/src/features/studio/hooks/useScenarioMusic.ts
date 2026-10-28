import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ScenarioMood } from "@/shared/types/audio.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import {
  confirmGeneratedTrack,
  discardMusicGenerationJob,
  getMusicQuota,
  listScenarioMusic,
  requestMusicGeneration,
  setDefaultMusicTrack,
  uploadMusicTrack,
} from "../api/music.api";
import { MusicGenerationRequest } from "../types/music.types";
import { requireScenarioId } from "../lib/requireScenarioId";
import { runChildWrite } from "../lib/childWrite";

export const useScenarioMusic = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const guardedWrite = <T,>(write: () => Promise<T>): Promise<T> =>
    runChildWrite(queryClient, requireScenarioId(scenarioId), write);
  const queryKey = ["scenario-music", scenarioId];
  const quotaQueryKey = ["scenario-music-quota", scenarioId];
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey });
    queryClient.invalidateQueries({ queryKey: quotaQueryKey });
  };

  const musicQuery = useQuery({
    queryKey,
    queryFn: () => listScenarioMusic(scenarioId as string),
    enabled: Boolean(scenarioId),
  });

  const quotaQuery = useQuery({
    queryKey: quotaQueryKey,
    queryFn: () => getMusicQuota(scenarioId as string),
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

  const generateMutation = useMutation({
    mutationFn: (payload: MusicGenerationRequest) =>
      requestMusicGeneration(requireScenarioId(scenarioId), payload),
    onSuccess: () => quotaQuery.refetch(),
  });

  const confirmMutation = useMutation({
    mutationFn: (jobId: string) =>
      guardedWrite(() => confirmGeneratedTrack(requireScenarioId(scenarioId), jobId)),
    onSuccess: invalidate,
  });

  const discardMutation = useMutation({
    mutationFn: (jobId: string) =>
      discardMusicGenerationJob(requireScenarioId(scenarioId), jobId),
    onSuccess: invalidate,
  });

  return {
    slots: musicQuery.data?.items ?? [],
    isLoading: musicQuery.isLoading,
    error: musicQuery.error,
    quota: quotaQuery.data ?? null,
    uploadTrack: uploadMutation.mutate,
    isUploading: uploadMutation.isPending,
    uploadError: uploadMutation.error
      ? extractErrorMessage(uploadMutation.error, "Failed to upload track.")
      : null,
    setDefaultTrack: setDefaultMutation.mutate,
    isSettingDefault: setDefaultMutation.isPending,
    requestGeneration: generateMutation.mutate,
    isRequestingGeneration: generateMutation.isPending,
    generationRequestError: generateMutation.error
      ? extractErrorMessage(
          generateMutation.error,
          "Failed to start music generation.",
        )
      : null,
    confirmGeneratedTrack: confirmMutation.mutate,
    isConfirming: confirmMutation.isPending,
    discardGenerationJob: discardMutation.mutate,
  };
};
