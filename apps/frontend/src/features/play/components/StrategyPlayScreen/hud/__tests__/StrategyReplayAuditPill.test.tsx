import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { StrategyReplayAuditPill } from "../StrategyReplayAuditPill";
import * as simulationApi from "../../../../api/simulation.api";

vi.mock("../../../../api/simulation.api", async (importOriginal) => {
  const actual = await importOriginal<typeof simulationApi>();
  return {
    ...actual,
    verifyPlaythroughReplay: vi.fn(),
  };
});

const mockedVerify = vi.mocked(simulationApi.verifyPlaythroughReplay);

describe("StrategyReplayAuditPill", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders idle state with 'Verify Replay'", () => {
    render(<StrategyReplayAuditPill playthroughId="pt-1" />);
    expect(screen.getByRole("button", { name: /verify replay/i })).toBeInTheDocument();
  });

  it("calls verifyPlaythroughReplay on click and displays verifying state, then verified state", async () => {
    const verifiedData = {
      verified_turn: 3,
      world_hash: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
      step_count: 24,
    };
    mockedVerify.mockResolvedValueOnce(verifiedData);
    const onVerified = vi.fn();

    render(
      <StrategyReplayAuditPill
        playthroughId="pt-1"
        throughTurn={3}
        onVerified={onVerified}
      />,
    );

    const button = screen.getByRole("button", { name: /verify replay/i });
    fireEvent.click(button);

    expect(screen.getByText(/verifying/i)).toBeInTheDocument();
    expect(mockedVerify).toHaveBeenCalledWith("pt-1", 3);

    await waitFor(() => {
      expect(screen.getByText(/verified turn 3/i)).toBeInTheDocument();
    });

    expect(onVerified).toHaveBeenCalledWith(verifiedData);
  });

  it("toggles audit popover on clicking the verified pill", async () => {
    mockedVerify.mockResolvedValueOnce({
      verified_turn: 2,
      world_hash: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
      step_count: 15,
    });

    render(<StrategyReplayAuditPill playthroughId="pt-1" />);
    fireEvent.click(screen.getByRole("button", { name: /verify replay/i }));

    await waitFor(() => {
      expect(screen.getByText(/verified turn 2/i)).toBeInTheDocument();
    });

    // Popover is closed initially or can be opened
    const verifiedBtn = screen.getByRole("button", { name: /verified turn 2/i });
    fireEvent.click(verifiedBtn);

    expect(screen.getByText(/mathematical replay verification/i)).toBeInTheDocument();
    expect(screen.getByText(/15 journal steps/i)).toBeInTheDocument();
    expect(screen.getByText(/1234567890abcdef/i)).toBeInTheDocument();
  });

  it("renders error state when verification fails", async () => {
    mockedVerify.mockRejectedValueOnce(new Error("Network Error"));

    render(<StrategyReplayAuditPill playthroughId="pt-1" />);
    fireEvent.click(screen.getByRole("button", { name: /verify replay/i }));

    await waitFor(() => {
      expect(screen.getByText(/verification failed/i)).toBeInTheDocument();
    });
  });

  it("renders disabled state when playthroughId is not provided", () => {
    render(<StrategyReplayAuditPill />);
    const btn = screen.getByRole("button", { name: /verify replay/i });
    expect(btn).toBeDisabled();
  });

  it("does not claim an older verification covers a newer turn", async () => {
    mockedVerify.mockResolvedValueOnce({ verified_turn: 3, world_hash: "abcdef1234", step_count: 5 });
    const { rerender } = render(<StrategyReplayAuditPill playthroughId="pt-1" throughTurn={3} />);
    fireEvent.click(screen.getByRole("button", { name: /verify replay/i }));
    await waitFor(() => expect(screen.getByText(/Verified Turn 3/)).toBeInTheDocument());

    rerender(<StrategyReplayAuditPill playthroughId="pt-1" throughTurn={4} />);

    expect(screen.queryByText(/Verified Turn 3/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Verify Turn 4 \(last: Turn 3\)/ })).toBeInTheDocument();
  });
});
