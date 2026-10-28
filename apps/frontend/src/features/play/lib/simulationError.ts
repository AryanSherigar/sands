import { isAxiosError } from "axios";
import { STALE_WORLD_STATUS } from "../constants/strategy.constants";

export interface SimulationErrorInfo {
  status: number | null;
  code: string | null;
  message: string;
  isStaleWorld: boolean;
}

interface SimulationErrorBody {
  detail?: unknown;
  code?: unknown;
}

export function parseSimulationError(error: unknown, fallback: string): SimulationErrorInfo {
  if (!isAxiosError<SimulationErrorBody>(error)) {
    return { status: null, code: null, message: fallback, isStaleWorld: false };
  }
  const status = error.response?.status ?? null;
  const body = error.response?.data;
  return {
    status,
    code: typeof body?.code === "string" ? body.code : null,
    message: typeof body?.detail === "string" ? body.detail : fallback,
    isStaleWorld: status === STALE_WORLD_STATUS,
  };
}
