import { apiClient } from "@/shared/lib/api-client";
import { ScenarioMood } from "@/shared/types/audio.types";
import {
  ScenarioMusicListResponse,
  ScenarioMusicSlot,
} from "../types/music.types";

export const listScenarioMusic = async (
  scenarioId: string,
): Promise<ScenarioMusicListResponse> => {
  const response = await apiClient.get<ScenarioMusicListResponse>(
    `/v1/scenarios/${scenarioId}/music`,
  );
  return response.data;
};

export const uploadMusicTrack = async (
  scenarioId: string,
  mood: ScenarioMood,
  file: File,
): Promise<ScenarioMusicSlot> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<ScenarioMusicSlot>(
    `/v1/scenarios/${scenarioId}/music/${mood}/upload`,
    formData,
    { headers: { "Content-Type": undefined } },
  );
  return response.data;
};

export const setDefaultMusicTrack = async (
  scenarioId: string,
  mood: ScenarioMood,
): Promise<ScenarioMusicSlot> => {
  const response = await apiClient.post<ScenarioMusicSlot>(
    `/v1/scenarios/${scenarioId}/music/${mood}/default`,
  );
  return response.data;
};
