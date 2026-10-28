import { useMutation } from "@tanstack/react-query";
import type {
  CreatePlaythroughPayload,
  PlaythroughResponse,
} from "@/shared/api/playthroughs.api";
import { startPlaytest } from "@/shared/api/playthroughs.api";

export const useCreatePlaytest = () =>
  useMutation<PlaythroughResponse, Error, CreatePlaythroughPayload>({
    mutationFn: ({ scenario_id, setup_values }) =>
      startPlaytest(scenario_id, setup_values),
  });
