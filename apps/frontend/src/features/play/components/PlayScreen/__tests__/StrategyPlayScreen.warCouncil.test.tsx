import { render, screen, fireEvent } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { StrategyPlayScreen } from "../StrategyPlayScreen";
import { DEFAULT_PREVIEW_WORLD } from "../../StrategyPlayScreen/defaultPreviewWorld";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "pt-123" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({
    data: {
      schema_version: 1,
      source: "manual",
      width: 1600,
      height: 900,
      image_url: "",
      regions: [
        {
          id: "ashford_ford",
          name: "Ashford Ridge",
          terrain: "plain",
          outline: "M 0 0 Z",
          label_point: { x: 100, y: 100 },
          neighbor_ids: [],
          source_color: null,
          source_ref: null,
        },
      ],
    },
  }),
}));

vi.mock("../../../hooks/useSimulationWorld", () => ({
  useSimulationWorld: () => ({
    data: {
      ...DEFAULT_PREVIEW_WORLD,
      turn: 1,
      status: "awaiting_battle_decision",
      orders_remaining: 3,
      my_faction: { ...DEFAULT_PREVIEW_WORLD.my_faction, id: "valenreach" },
      battles: [
        {
          id: "battle-1",
          region_id: "ashford_ford",
          is_big: true,
          control_mode: "undecided",
          status: "awaiting_commands",
        },
      ],
      armies: [],
      queued_orders: [],
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useBattleControl", () => ({
  useBattleControl: () => ({
    choose: vi.fn(),
    isPending: false,
    errorInfo: null,
  }),
}));

const BATTLE_URL = "/simulation/v1/playthroughs/pt-123/battles/battle-1";
const FIELD_BATTLE = {
  id: "battle-1",
  region_id: "ashford_ford",
  status: "awaiting_commands",
  outcome: null,
  current_turn: 1,
  exchanges_used: 0,
  total_exchanges: 0,
  is_big: true,
  control_mode: "player",
  terrain: "hills",
  weather: "rain",
  command_cost: 1,
  own_contingent: {
    faction_id: "valenreach",
    army_ids: [],
    troops: { infantry: 1000, cavalry: 200, archers_siege: 300 },
    morale: 90,
    fatigue: 5,
    plan: {
      formation: "defensive",
      tactic: "hold",
      withdrawal_policy: "balanced",
      reserve_policy: "conserve",
    },
    supply: "supplied",
    status: "fighting",
  },
  opponents: [{ faction_id: "ironmark", strength: { minimum: 900, maximum: 1300 }, reports: [] }],
  legal_commands: ["set_plan", "withdraw"],
};

describe("StrategyPlayScreen War Council Integration", () => {
  it("opens War Council screen when taking command of a battle and returns to map", async () => {
    server.use(
      http.get(BATTLE_URL, () => HttpResponse.json(FIELD_BATTLE)),
      http.get(`${BATTLE_URL}/reports`, () => HttpResponse.json({ items: [] })),
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <StrategyPlayScreen />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Your armies await orders")).toBeInTheDocument();
    const takeCmdBtn = screen.getByText("Take command");
    fireEvent.click(takeCmdBtn);

    expect(await screen.findByText("Battle of Ashford Ridge")).toBeInTheDocument();
    expect(screen.getByText("Commit to Battle")).toBeInTheDocument();

    const returnBtn = screen.getByText("Map of Ashford Ridge");
    fireEvent.click(returnBtn);

    expect(screen.queryByText("Commit to Battle")).not.toBeInTheDocument();
  });
});
