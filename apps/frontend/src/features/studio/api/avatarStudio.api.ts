import { apiClient } from "@/shared/lib/api-client";
import { AVATAR_BUILD_TIMEOUT_MS, IMAGE_GENERATION_TIMEOUT_MS } from "../constants/upload";
import type { PremadeAvatar, PremadeAvatarListResponse } from "../types/premade_avatar.types";

export interface OptimizePromptResponse {
  optimized_prompt: string;
}

export interface BuildMeshResponse {
  avatar_url: string;
  name: string;
}

export const optimizeAvatarPrompt = async (description: string): Promise<string> => {
  const response = await apiClient.post<OptimizePromptResponse>(
    "/v1/studio/avatars/optimize-prompt",
    { description },
  );
  return response.data.optimized_prompt;
};

export const buildMeshAvatar = async (
  name: string,
  imageUrl: string,
): Promise<BuildMeshResponse> => {
  const response = await apiClient.post<BuildMeshResponse>(
    "/v1/studio/avatars/build-mesh",
    { name, image_url: imageUrl },
    { timeout: AVATAR_BUILD_TIMEOUT_MS },
  );
  return response.data;
};

export interface GeneratePortraitResponse {
  image_url: string;
}

export const generateLeaderPortrait = async (prompt: string): Promise<string> => {
  const response = await apiClient.post<GeneratePortraitResponse>(
    "/v1/studio/avatars/generate-portrait",
    { prompt },
    { timeout: IMAGE_GENERATION_TIMEOUT_MS },
  );
  return response.data.image_url;
};

export const listPremadeAvatars = async (): Promise<PremadeAvatar[]> => {
  const response = await apiClient.get<PremadeAvatarListResponse>(
    "/v1/studio/avatars/premade",
  );
  return response.data.avatars;
};
