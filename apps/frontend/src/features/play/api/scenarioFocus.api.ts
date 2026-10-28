export { toggleBookmarkApi } from "@/shared/api/scenarios.api";
import { apiClient } from "@/shared/lib/api-client";
import {
  PublicPlaythroughSummary,
  ScenarioDetailResponse,
  ScenarioEndingsResponse,
  ScenarioReviewListResponse,
  ScenarioReviewResponse,
} from "../types/scenario";

export const fetchScenarioDetail = async (
  scenarioId: string,
): Promise<ScenarioDetailResponse> => {
  const response = await apiClient.get<ScenarioDetailResponse>(
    `/v1/scenarios/${scenarioId}`,
  );
  return response.data;
};

export const fetchScenarioReviews = async (
  scenarioId: string,
  limit: number,
  offset: number,
): Promise<ScenarioReviewListResponse> => {
  const response = await apiClient.get<ScenarioReviewListResponse>(
    `/v1/scenarios/${scenarioId}/reviews`,
    { params: { limit, offset } },
  );
  return response.data;
};

export const submitScenarioReview = async (
  scenarioId: string,
  rating: number,
  comment?: string,
): Promise<ScenarioReviewResponse> => {
  const response = await apiClient.post<ScenarioReviewResponse>(
    `/v1/scenarios/${scenarioId}/reviews`,
    { rating, comment },
  );
  return response.data;
};

export const fetchPublicPlaythroughs = async (
  scenarioId: string,
): Promise<PublicPlaythroughSummary[]> => {
  const response = await apiClient.get<PublicPlaythroughSummary[]>(
    `/v1/scenarios/${scenarioId}/playthroughs`,
  );
  return response.data;
};

export const fetchScenarioEndings = async (
  scenarioId: string,
): Promise<ScenarioEndingsResponse> => {
  const response = await apiClient.get<ScenarioEndingsResponse>(
    `/v1/scenarios/${scenarioId}/endings`,
  );
  return response.data;
};
