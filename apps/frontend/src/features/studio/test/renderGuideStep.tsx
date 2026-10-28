import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { GuideScenarioProvider } from "../components/Guide/GuideScenarioProvider";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "./studioApiMock";

type StudioApiInit = Parameters<typeof installStudioApi>[0];

const WAIT = { timeout: 4000 };

export const renderGuideStep = async (
  step: React.ReactElement,
  init: StudioApiInit = {},
) => {
  useStudioTabsStore.getState().resetTabs();
  const api = installStudioApi({
    scenario: buildScenarioFixture({ mode: "master" }),
    ...init,
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const user = userEvent.setup();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <GuideScenarioProvider scenarioId={STUDIO_TEST_SCENARIO_ID} onDraftCreated={() => undefined}>
          {step}
        </GuideScenarioProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await waitFor(
    () => expect(queryClient.getQueryData(["scenario", STUDIO_TEST_SCENARIO_ID])).toBeDefined(),
    WAIT,
  );
  return { api, user, queryClient, ...view };
};
