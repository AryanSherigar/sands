import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ScenarioResponse } from "../../../types/scenario.types";
import type { PublishReport } from "../../../types/strategyDocument.types";
import { StrategyPublishSection } from "../StrategyPublishSection";

const publish = vi.fn();
vi.mock("../../../hooks/usePublish", () => ({
  usePublish: () => ({
    publish,
    isTriggering: false,
    isPolling: false,
    status: "idle",
    triggerError: null,
    publishError: null,
  }),
}));

const SCENARIO = { scenario_id: "s1", content_tag: "general" } as ScenarioResponse;
const CLEAN: PublishReport = { blocking: [], warnings: [] };
const BLOCKED: PublishReport = {
  blocking: [{ code: "x", message: "Needs a faction", path: [] } as never],
  warnings: [],
};

function renderSection(onFlush: () => Promise<boolean>, onRecheck: () => Promise<PublishReport | undefined>) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <StrategyPublishSection
        scenario={SCENARIO}
        report={CLEAN}
        isMapMissing={false}
        onFlush={onFlush}
        onRecheck={onRecheck}
        onOpenPanel={vi.fn()}
      />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Publish" }));
}

describe("StrategyPublishSection", () => {
  it("does not publish when the latest save failed", async () => {
    publish.mockClear();
    renderSection(vi.fn().mockResolvedValue(false), vi.fn());

    expect(await screen.findByText(/could not be saved/i)).toBeInTheDocument();
    expect(publish).not.toHaveBeenCalled();
  });

  it("does not publish when the fresh check has blocking issues", async () => {
    publish.mockClear();
    renderSection(vi.fn().mockResolvedValue(true), vi.fn().mockResolvedValue(BLOCKED));

    expect(await screen.findByText(/must be fixed before publishing/i)).toBeInTheDocument();
    expect(publish).not.toHaveBeenCalled();
  });

  it("publishes after a successful save and a clean fresh check", async () => {
    publish.mockClear();
    renderSection(vi.fn().mockResolvedValue(true), vi.fn().mockResolvedValue(CLEAN));

    await waitFor(() => expect(publish).toHaveBeenCalledTimes(1));
  });
});
