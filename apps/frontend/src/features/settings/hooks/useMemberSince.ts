import { useQuery } from "@tanstack/react-query";
import { fetchAccountSummary } from "@/shared/api/userPreferences.api";

const MEMBER_SINCE_FORMAT: Intl.DateTimeFormatOptions = {
  month: "short",
  year: "numeric",
};
const ACCOUNT_SUMMARY_STALE_MS = 1000 * 60 * 10;

export const useMemberSince = (): string | null => {
  const { data } = useQuery({
    queryKey: ["account-summary"],
    queryFn: fetchAccountSummary,
    staleTime: ACCOUNT_SUMMARY_STALE_MS,
  });
  if (!data?.created_at) return null;
  return new Date(data.created_at).toLocaleDateString(undefined, MEMBER_SINCE_FORMAT);
};
