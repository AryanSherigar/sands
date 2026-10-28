import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { usePlayStore } from "../../../stores/play.store";
import type { PlaythroughData } from "../../../types/play.types";
import { MemoryDegradedBanner } from "../MemoryDegradedBanner";

const RETRY_URL = "*/v1/playthroughs/pt-1/memory/retry";
const BANNER_TEXT = /Some story memory is catching up/;

function playthrough(overrides: Partial<PlaythroughData> = {}): PlaythroughData {
  return { playthrough_id: "pt-1", is_spectator: false, ...overrides } as PlaythroughData;
}

function renderBanner() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryDegradedBanner />
    </QueryClientProvider>,
  );
}

describe("MemoryDegradedBanner", () => {
  beforeEach(() => {
    usePlayStore.setState({
      playthrough: playthrough(),
      memory_degraded_reasons: [],
    });
  });

  it("renders nothing while memory is keeping up", () => {
    renderBanner();

    expect(screen.queryByText(BANNER_TEXT)).not.toBeInTheDocument();
  });

  it("shows the notice and a retry action when memory is degraded", () => {
    usePlayStore.setState({ memory_degraded_reasons: ["extraction_failed"] });

    renderBanner();

    expect(screen.getByText(BANNER_TEXT)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry memory" })).toBeEnabled();
  });

  it("hides for spectators, who cannot retry", () => {
    usePlayStore.setState({
      playthrough: playthrough({ is_spectator: true }),
      memory_degraded_reasons: ["extraction_failed"],
    });

    renderBanner();

    expect(screen.queryByText(BANNER_TEXT)).not.toBeInTheDocument();
  });

  it("clears the notice when the retry resolves every reason", async () => {
    server.use(
      http.post(RETRY_URL, () => HttpResponse.json({ degraded_reasons: [] })),
    );
    usePlayStore.setState({ memory_degraded_reasons: ["extraction_failed"] });
    renderBanner();

    await userEvent.click(screen.getByRole("button", { name: "Retry memory" }));

    await waitFor(() =>
      expect(screen.queryByText(BANNER_TEXT)).not.toBeInTheDocument(),
    );
  });

  it("keeps the notice when reasons remain after the retry", async () => {
    server.use(
      http.post(RETRY_URL, () =>
        HttpResponse.json({ degraded_reasons: ["indexing_lag"] }),
      ),
    );
    usePlayStore.setState({ memory_degraded_reasons: ["extraction_failed"] });
    renderBanner();

    await userEvent.click(screen.getByRole("button", { name: "Retry memory" }));

    await waitFor(() =>
      expect(usePlayStore.getState().memory_degraded_reasons).toEqual([
        "indexing_lag",
      ]),
    );
    expect(screen.getByText(BANNER_TEXT)).toBeInTheDocument();
  });

  it("says memory is unreachable when the retry call fails, and play stays possible", async () => {
    server.use(http.post(RETRY_URL, () => new HttpResponse(null, { status: 502 })));
    usePlayStore.setState({ memory_degraded_reasons: ["extraction_failed"] });
    renderBanner();

    await userEvent.click(screen.getByRole("button", { name: "Retry memory" }));

    expect(await screen.findByText(/Couldn't reach story memory/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry memory" })).toBeEnabled();
  });
});
