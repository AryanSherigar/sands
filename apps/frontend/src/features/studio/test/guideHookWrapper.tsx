import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { GuideScenarioProvider } from "../components/Guide/GuideScenarioProvider";
import { STUDIO_TEST_SCENARIO_ID } from "./studioApiMock";

export const createGuideWrapper = (scenarioId: string = STUDIO_TEST_SCENARIO_ID) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <GuideScenarioProvider scenarioId={scenarioId} onDraftCreated={() => undefined}>
        {children}
      </GuideScenarioProvider>
    </QueryClientProvider>
  );
  return { Wrapper, queryClient };
};
