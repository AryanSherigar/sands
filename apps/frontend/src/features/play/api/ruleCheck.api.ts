import { useAuthStore } from "@/features/auth/stores/auth.store";
import { buildTrsAuthHeaders } from "@/shared/lib/sse-client";
import type { RuleCheckArmedPayload } from "@/shared/types/check.types";

const TRS_BASE_URL = import.meta.env.VITE_TRS_URL || "http://localhost:8001";

class RuleCheckArmError extends Error {}

export interface ArmRuleCheckParams {
  playthrough_id: string;
  participant_id: string;
  check_id: string;
}

export async function armRuleCheck(
  params: ArmRuleCheckParams,
): Promise<RuleCheckArmedPayload> {
  const accessToken = useAuthStore.getState().accessToken;
  const response = await fetch(`${TRS_BASE_URL}/v1/turn/rule-check/arm`, {
    method: "POST",
    headers: {
      ...buildTrsAuthHeaders(accessToken),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new RuleCheckArmError(`Arming failed: ${response.status}`);
  }
  return (await response.json()) as RuleCheckArmedPayload;
}
