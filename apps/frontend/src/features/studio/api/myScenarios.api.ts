import { apiClient } from "@/shared/lib/api-client";
import type {
  MyScenarioListResponse,
  StudioTab,
} from "../types/scenario.types";

export interface ListMyScenariosParams {
  tab: StudioTab;
  query: string;
  limit: number;
  offset: number;
}

export const listMyScenarios = async ({
  tab,
  query,
  limit,
  offset,
}: ListMyScenariosParams): Promise<MyScenarioListResponse> => {
  const response = await apiClient.get<MyScenarioListResponse>("/v1/scenarios", {
    params: {
      mine: true,
      sort: "edited",
      tab: tab === "all" ? undefined : tab,
      q: query || undefined,
      limit,
      offset,
    },
  });
  return response.data;
};
