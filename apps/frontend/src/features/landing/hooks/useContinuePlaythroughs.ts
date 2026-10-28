import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchUserPlaythroughs } from "@/shared/api/playthroughs.api";
import { useIsAuthenticated } from "@/shared/hooks/useIsAuthenticated";
import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";
import { CONTINUE_ROW_LIMIT } from "../constants/landing.constants";

const ACTIVE_STATUS = "active";

const selectMostRecent = (
  playthroughs: UserPlaythroughSummary[],
): UserPlaythroughSummary[] =>
  [...playthroughs]
    .sort((first, second) => second.updated_at.localeCompare(first.updated_at))
    .slice(0, CONTINUE_ROW_LIMIT);

export const useContinuePlaythroughs = (): UseQueryResult<
  UserPlaythroughSummary[],
  Error
> => {
  const isAuthenticated = useIsAuthenticated();
  return useQuery<UserPlaythroughSummary[], Error>({
    queryKey: ["user-playthroughs", ACTIVE_STATUS],
    queryFn: () => fetchUserPlaythroughs(ACTIVE_STATUS),
    select: selectMostRecent,
    staleTime: 0,
    enabled: isAuthenticated,
  });
};
