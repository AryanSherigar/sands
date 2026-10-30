import type React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrategyRightDrawer } from "../StrategyRightDrawer";
import type { CampaignWorldView } from "../../../../types/simulation.types";

const mockRivals = [
  {
    faction_id: "f-oakhaven",
    name: "Duchy of Oakhaven",
    leader_name: "Duke Cedric",
    relation: "alliance",
    opinion: 45,
    treasury_range: { low: 200, high: 400 },
    manpower_range: { low: 10000, high: 15000 },
  },
];

const mockWorld = {
  turn: 1,
  orders_remaining: 3,
  my_faction: {
    id: "f-1",
    leader_id: null,
    treasury: 400,
    manpower: 5000,
    stability: 60,
    war_exhaustion: 10,
    reputation: 0,
    tax_rate: "normal",
    loans: [],
  },
  ruler: { name: "King Aldric" },
  regions: [],
  armies: [],
  rivals: [],
  pacts: [],
  clock: { turn: 1, start_year: 1042, start_month: 3 },
} as unknown as CampaignWorldView;

function renderDrawer(node: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

describe("StrategyRightDrawer", () => {
  it("renders factions tab and rival item", () => {
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab="factions"
        isPinned={false}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );
    expect(screen.getByText("Duchy of Oakhaven")).toBeInTheDocument();
  });

  it("handles tab selection and pin toggling", () => {
    const onSelectTab = vi.fn();
    const onTogglePin = vi.fn();
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab="factions"
        isPinned={false}
        onSelectTab={onSelectTab}
        onTogglePin={onTogglePin}
        onJumpToRegion={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /chronicle/i }));
    expect(onSelectTab).toHaveBeenCalledWith("chronicle");

    fireEvent.click(screen.getByRole("button", { name: /pin/i }));
    expect(onTogglePin).toHaveBeenCalled();
  });

  it("renders an empty chronicle without fabricated entries", () => {
    const onJumpToRegion = vi.fn();
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab="chronicle"
        isPinned={false}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={onJumpToRegion}
      />,
    );
    expect(screen.getByLabelText("Chronicle")).toBeInTheDocument();
    expect(screen.getByText("No chronicle entries yet")).toBeInTheDocument();
    expect(onJumpToRegion).not.toHaveBeenCalled();
  });

  it("toggles active factions tab off when clicked again", () => {
    const onSelectTab = vi.fn();
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab="factions"
        isPinned={false}
        onSelectTab={onSelectTab}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /factions/i }));
    expect(onSelectTab).toHaveBeenCalledWith(null);
  });

  it("renders treasury tab button", () => {
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab={null}
        isPinned={false}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Treasury/i })).toBeInTheDocument();
  });

  it("calls onSelectTab with 'treasury' when Treasury tab is clicked", () => {
    const onSelectTab = vi.fn();
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab={null}
        isPinned={false}
        onSelectTab={onSelectTab}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Treasury/i }));
    expect(onSelectTab).toHaveBeenCalledWith("treasury");
  });

  it("renders royal exchequer panel when activeTab is treasury", () => {
    renderDrawer(
      <StrategyRightDrawer
        rivals={mockRivals}
        activeTab="treasury"
        isPinned={false}
        world={mockWorld}
        onSubmitOrder={vi.fn()}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );
    expect(screen.getByText("Royal Exchequer")).toBeInTheDocument();
    expect(screen.getByText(/Tax Rate/i)).toBeInTheDocument();
  });

  it("renders pending war call and handles honour call and refuse", () => {
    const mockSubmitOrder = vi.fn();
    const worldWithCall = {
      ...mockWorld,
      pending_calls: [
        {
          id: "call-1",
          caller_id: "faction-mira",
          war_id: "war-1",
          side: "defender" as const,
          is_defensive: true,
          deadline_turn: 5,
        },
      ],
      rivals: [
        {
          faction_id: "faction-mira",
          name: "Dunmere",
          leader_name: "Lady Mira",
          relation: "alliance",
          treasury_range: { low: 100, high: 200 },
          manpower_range: { low: 1000, high: 2000 },
        },
      ],
    };

    renderDrawer(
      <StrategyRightDrawer
        rivals={worldWithCall.rivals}
        activeTab="factions"
        isPinned={false}
        world={worldWithCall}
        onSubmitOrder={mockSubmitOrder}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );

    expect(screen.getByText(/War Call from Dunmere/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Honour Call/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "answer_call", call_id: "call-1", is_joining: true }),
    );

    fireEvent.click(screen.getByRole("button", { name: /Refuse/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "answer_call", call_id: "call-1", is_joining: false }),
    );
  });

  it("renders pending demand and handles comply and refuse", () => {
    const mockSubmitOrder = vi.fn();
    const worldWithDemand = {
      ...mockWorld,
      pending_demands: [
        {
          id: "demand-1",
          overlord_id: "faction-mira",
          kind: "gold" as const,
          amount: 250,
          granted: 0,
          deadline_turn: 3,
        },
      ],
      rivals: [
        {
          faction_id: "faction-mira",
          name: "Dunmere",
          leader_name: "Lady Mira",
          relation: "vassal",
          treasury_range: { low: 100, high: 200 },
          manpower_range: { low: 1000, high: 2000 },
        },
      ],
    };

    renderDrawer(
      <StrategyRightDrawer
        rivals={worldWithDemand.rivals}
        activeTab="factions"
        isPinned={false}
        world={worldWithDemand}
        onSubmitOrder={mockSubmitOrder}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );

    expect(screen.getByText(/Demand from Dunmere/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Comply/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "answer_demand", demand_id: "demand-1", reply: "accept" }),
    );

    fireEvent.click(screen.getByRole("button", { name: /Refuse/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "answer_demand", demand_id: "demand-1", reply: "refuse" }),
    );
  });

  it("shows obligations count badge when pending calls or demands exist", () => {
    const worldWithObligations = {
      ...mockWorld,
      pending_calls: [
        {
          id: "call-1",
          caller_id: "faction-mira",
          war_id: "war-1",
          side: "defender" as const,
          is_defensive: true,
          deadline_turn: 5,
        },
      ],
      pending_demands: [
        {
          id: "demand-1",
          overlord_id: "faction-mira",
          kind: "gold" as const,
          amount: 250,
          granted: 0,
          deadline_turn: 3,
        },
      ],
    };

    renderDrawer(
      <StrategyRightDrawer
        rivals={[]}
        activeTab="factions"
        isPinned={false}
        world={worldWithObligations}
        onSubmitOrder={vi.fn()}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );

    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders rival actions based on war/peace state", () => {
    const mockSubmitOrder = vi.fn();
    const onProposeTerms = vi.fn();
    const rivals = [
      {
        faction_id: "f-war",
        name: "Enemy Clan",
        leader_name: "Warlord",
        relation: "at_war",
        treasury_range: { low: 100, high: 200 },
        manpower_range: { low: 1000, high: 2000 },
      },
      {
        faction_id: "f-peace",
        name: "Friendly State",
        leader_name: "Governor",
        relation: "peace",
        treasury_range: { low: 100, high: 200 },
        manpower_range: { low: 1000, high: 2000 },
      },
    ];

    renderDrawer(
      <StrategyRightDrawer
        rivals={rivals}
        activeTab="factions"
        isPinned={false}
        world={mockWorld}
        diplomacy={{ pacts: [], isProposalAvailable: true, onProposeTerms }}
        onSubmitOrder={mockSubmitOrder}
        onSelectTab={vi.fn()}
        onTogglePin={vi.fn()}
        onJumpToRegion={vi.fn()}
      />,
    );

    // At war: "Sue for Peace" and "Peace Talks"
    expect(screen.getByRole("button", { name: /Sue for Peace/i })).toBeInTheDocument();
    const peaceTalksBtn = screen.getByRole("button", { name: /Peace Talks/i });
    expect(peaceTalksBtn).toBeInTheDocument();
    fireEvent.click(peaceTalksBtn);
    expect(onProposeTerms).toHaveBeenCalledWith("f-war");

    fireEvent.click(screen.getByRole("button", { name: /Sue for Peace/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "sue_peace" }),
    );

    // At peace: "Propose terms", "Send Envoy", and "Declare War"
    expect(screen.getByRole("button", { name: /Propose terms/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Send Envoy/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Declare War/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Send Envoy/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "send_envoy", target_faction_id: "f-peace" }),
    );

    fireEvent.click(screen.getByRole("button", { name: /Declare War/i }));
    expect(mockSubmitOrder).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "declare_war", target_faction_id: "f-peace" }),
    );
  });
});
