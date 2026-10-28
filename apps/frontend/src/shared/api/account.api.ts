import { apiClient } from "@/shared/lib/api-client";

export const deleteMyAccount = async (): Promise<void> => {
  await apiClient.delete("/v1/users/me");
};
