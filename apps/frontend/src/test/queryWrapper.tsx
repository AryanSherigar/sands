import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ALPHA_CONFIG_QUERY_KEY } from "@/shared/hooks/useAlphaConfig";
import type { AlphaConfig } from "@/shared/types/alpha.types";

export function createQueryWrapper(
  alphaConfig?: AlphaConfig,
): React.FC<{ children: React.ReactNode }> {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  if (alphaConfig) client.setQueryData(ALPHA_CONFIG_QUERY_KEY, alphaConfig);
  return function QueryWrapper({ children }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}
