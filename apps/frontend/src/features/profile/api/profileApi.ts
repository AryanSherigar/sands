export { fetchUserPlaythroughs } from "@/shared/api/playthroughs.api";
import { apiClient } from "@/shared/lib/api-client";
import type {
  AchievementItem,
  OwnerAchievementDto,
  PublicAchievementDto,
} from "../types/achievements.types";
import type { ProfileEndings } from "../types/endings.types";
import type { ProfileOverview } from "../types/overview.types";
import {
  UserProfile,
  UserProfileUpdatePayload,
  UserReviewSummary,
} from "../types/profile.types";

export const fetchMyProfile = async (): Promise<UserProfile> => {
  const { data } = await apiClient.get<UserProfile>("/v1/users/me");
  return data;
};

export const fetchPublicProfile = async (
  userId: string,
): Promise<UserProfile> => {
  const { data } = await apiClient.get<UserProfile>(`/v1/users/${userId}`);
  return data;
};

export const updateProfile = async (
  payload: UserProfileUpdatePayload,
): Promise<UserProfile> => {
  const { data } = await apiClient.patch<UserProfile>("/v1/users/me", payload);
  return data;
};

export const fetchUserReviews = async (
  userId: string,
): Promise<UserReviewSummary[]> => {
  const { data } = await apiClient.get<UserReviewSummary[]>(
    `/v1/users/${userId}/reviews`,
  );
  return data;
};

export const abandonPlaythrough = async (
  playthroughId: string,
): Promise<void> => {
  await apiClient.post(`/v1/playthroughs/${playthroughId}/abandon`);
};

export const uploadAvatar = async (file: File): Promise<string> => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<{ url: string }>(
    "/v1/uploads/avatar",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
  return data.url;
};

export const uploadBanner = async (file: File): Promise<string> => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<{ url: string }>(
    "/v1/uploads/banner",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
  return data.url;
};

export const fetchMyOverview = async (): Promise<ProfileOverview> => {
  const { data } = await apiClient.get<ProfileOverview>(
    "/v1/users/me/overview",
  );
  return data;
};

export const fetchMyEndings = async (): Promise<ProfileEndings> => {
  const { data } = await apiClient.get<ProfileEndings>("/v1/users/me/endings");
  return data;
};

export const fetchMyAchievements = async (): Promise<AchievementItem[]> => {
  const { data } = await apiClient.get<OwnerAchievementDto[]>(
    "/v1/users/me/achievements",
  );
  return data;
};

export const fetchPublicAchievements = async (
  userId: string,
): Promise<AchievementItem[]> => {
  const { data } = await apiClient.get<PublicAchievementDto[]>(
    `/v1/users/${userId}/achievements`,
  );
  return data.map((dto) => ({ ...dto, progress: null }));
};
