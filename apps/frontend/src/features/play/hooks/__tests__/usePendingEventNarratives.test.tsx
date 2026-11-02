import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as eventsApi from "../../api/strategyEvents.api";
import { makePendingEvent } from "../../test-utils/eventFixtures";
import { usePendingEventNarratives } from "../usePendingEventNarratives";

vi.mock("../../api/strategyEvents.api", () => ({ requestEventNarrative: vi.fn() }));

const NARRATIVE = {
  body_prose: "A dark omen.",
  cause_quote: "Beware.",
  character_name: "Elder",
  character_title: "Hermit",
  disposition: "Grim",
};

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe("usePendingEventNarratives", () => {
  beforeEach(() => {
    vi.mocked(eventsApi.requestEventNarrative).mockReset();
  });

  it("requests prose once for events that have none, including after a reload", async () => {
    vi.mocked(eventsApi.requestEventNarrative).mockResolvedValue(NARRATIVE);
    const events = [makePendingEvent({ id: "event_pe_1", narrative: null })];
    const { rerender } = renderHook(() => usePendingEventNarratives("pt-1", events), { wrapper });

    await waitFor(() => expect(eventsApi.requestEventNarrative).toHaveBeenCalledWith("pt-1", "event_pe_1"));
    rerender();

    expect(eventsApi.requestEventNarrative).toHaveBeenCalledTimes(1);
  });

  it("skips events that already have prose", () => {
    const events = [makePendingEvent({ id: "event_pe_2", narrative: NARRATIVE })];
    renderHook(() => usePendingEventNarratives("pt-1", events), { wrapper });

    expect(eventsApi.requestEventNarrative).not.toHaveBeenCalled();
  });

  it("allows a retry after a failed request", async () => {
    vi.mocked(eventsApi.requestEventNarrative).mockResolvedValueOnce(null).mockResolvedValue(NARRATIVE);
    const first = [makePendingEvent({ id: "event_pe_3", narrative: null })];
    const { rerender } = renderHook(({ events }) => usePendingEventNarratives("pt-1", events), {
      wrapper,
      initialProps: { events: first },
    });
    await waitFor(() => expect(eventsApi.requestEventNarrative).toHaveBeenCalledTimes(1));

    rerender({ events: [...first] });

    await waitFor(() => expect(eventsApi.requestEventNarrative).toHaveBeenCalledTimes(2));
  });
});
