import type { QueryClient } from "@tanstack/react-query";
import { runGuardedWrite } from "./editGuard";

export const runChildWrite = <T>(
  queryClient: QueryClient,
  scenarioId: string,
  write: () => Promise<T>,
): Promise<T> =>
  runGuardedWrite(queryClient, scenarioId, () => write(), { shouldRefreshStamp: true });
