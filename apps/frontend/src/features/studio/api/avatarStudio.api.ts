import { apiClient } from "@/shared/lib/api-client";

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
  );
  return response.data.image_url;
};
