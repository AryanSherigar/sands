import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { StrategyPlayScreen } from "../StrategyPlayScreen";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import { makePendingEvent } from "../../../test-utils/eventFixtures";
import type { CampaignWorldView } from "../../../types/simulation.types";

const FACTION = "f1";
const mocks = vi.hoisted(() => ({
  world: { current: null as unknown },
  check: vi.fn(),
  mutateAsync: vi.fn(),
  cancel: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-playthrough" }),
  useNavigate: () => vi.fn(),
}));
vi.mock("../../../hooks/useSimulationWorld", () => ({
  useSimulationWorld: () => ({
    data: mocks.world.current,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));
vi.mock("../../../hooks/useEndTurn", () => ({
  useEndTurn: () => ({ endTurn: vi.fn(), isEndingTurn: false, errorInfo: null }),
}));
vi.mock("../../../hooks/useSimulationCommands", () => ({
  useSimulationCommands: () => ({
    acceptMutation: { mutate: vi.fn(), mutateAsync: mocks.mutateAsync, isPending: false },
    cancelMutation: { mutate: mocks.cancel, isPending: false },
    check: mocks.check,
  }),
}));
vi.mock("../../../hooks/useStrategyEvent", () => ({
  useStrategyEvent: () => ({ eventPackage: null, isResolving: false, resolveChoice: vi.fn() }),
}));
vi.mock("../../../hooks/useStrategyDiplomacy", () => ({
  useStrategyDiplomacy: () => ({
    diplomacy: { pacts: [], isProposalAvailable: false, onProposeTerms: vi.fn() },
    sceneId: null,
    errorMessage: null,
  }),
}));
vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({ data: null, isLoading: false, isError: false }),
}));

function worldWithEvent(overrides = {}): CampaignWorldView {
  return {
    world_version: 1,
    turn: 5,
    wave: 0,
    status: "planning",
    battles: [],
    clock: { turn: 5, start_year: 1042, start_month: 7 },
    my_faction: {
      id: FACTION,
      treasury: 340,
      manpower: 100,
      stability: 50,
      war_exhaustion: 0,
      reputation: 0,
      tax_rate: "normal",
      loans: [],
    },
    ruler: { name: "King Alden IV" },
    regions: [],
    armies: [],
    rivals: [],
    queued_orders: [],
    orders_remaining: 4,
    pending_events: [makePendingEvent(overrides)],
  } as unknown as CampaignWorldView;
}

describe("StrategyPlayScreen events", () => {
  beforeEach(() => {
    useStrategyPlayStore.getState().reset();
    mocks.check.mockReset().mockResolvedValue({ flag: null, orders_remaining: 4 });
    mocks.mutateAsync.mockReset().mockResolvedValue({});
    mocks.cancel.mockReset();
    mocks.world.current = worldWithEvent();
  });

  it("queues an answer order from a situation lever after a dry-run check", async () => {
    useStrategyPlayStore.getState().openSituations();
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getAllByRole("button", { name: "Order this" })[0]);
    const expected = {
      kind: "answer_event",
      faction_id: FACTION,
      event_id: "event_1",
      choice_id: "ease_taxes",
    };
    await waitFor(() => expect(mocks.mutateAsync).toHaveBeenCalledWith(expected));
    expect(mocks.check).toHaveBeenCalledWith(expected);
  });

  it("does not queue an answer the server flags as impossible", async () => {
    mocks.check.mockResolvedValue({ flag: "over_budget", reason: "insufficient_points" });
    useStrategyPlayStore.getState().openSituations();
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getAllByRole("button", { name: "Order this" })[0]);
    await waitFor(() => expect(mocks.check).toHaveBeenCalled());
    expect(mocks.mutateAsync).not.toHaveBeenCalled();
  });

  it("opens the decision from the escalation banner and answers by number key", async () => {
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getByRole("button", { name: "Review decision" }));
    expect(await screen.findByRole("dialog")).toBeDefined();
    expect(screen.getByText("If you leave this unanswered: Unrest +10, Governor opinion −10"))
      .toBeDefined();
    fireEvent.keyDown(window, { key: "2" });
    await waitFor(() =>
      expect(mocks.mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({ kind: "answer_event", choice_id: "garrison_crackdown" }),
      ),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("closes the decision without ordering anything on Escape", async () => {
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getByRole("button", { name: "Review decision" }));
    await screen.findByRole("dialog");
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(mocks.mutateAsync).not.toHaveBeenCalled();
  });

  it("cancels a queued answer from the situations drawer", () => {
    mocks.world.current = worldWithEvent({
      queued_choice_id: "ease_taxes",
      queued_command_id: "cmd-5",
    });
    useStrategyPlayStore.getState().openSituations();
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getByRole("button", { name: /Queued — cancel/ }));
    expect(mocks.cancel).toHaveBeenCalledWith("cmd-5");
  });

  it("shows the real orders left in the situations drawer", () => {
    useStrategyPlayStore.getState().openSituations();
    render(<StrategyPlayScreen />);
    expect(screen.getByText("Orders left: 4. You cannot mend everything.")).toBeDefined();
  });
});
