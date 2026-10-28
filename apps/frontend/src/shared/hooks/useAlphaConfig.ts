import { useQuery } from "@tanstack/react-query";
import { fetchAlphaConfig } from "../api/alpha.api";

export const ALPHA_CONFIG_QUERY_KEY = ["alpha-config"];

const ALPHA_CONFIG_STALE_TIME_MS = 5 * 60 * 1000;

export function useAlphaConfig() {
  return useQuery({
    queryKey: ALPHA_CONFIG_QUERY_KEY,
    queryFn: fetchAlphaConfig,
    staleTime: ALPHA_CONFIG_STALE_TIME_MS,
  });
}
