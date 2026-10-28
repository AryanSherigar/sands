import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SetupPage } from "../SetupPage";

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: "strat-1" }),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

vi.mock("@/features/auth/hooks/useAuth", () => ({
  useAuth: () => ({ isLoading: false, user: { user_id: "user-1" } }),
}));

vi.mock("@/shared/hooks/useRequireAuth", () => ({
  useRequireAuth: () => vi.fn().mockResolvedValue(true),
}));

const mockMutateAsync = vi.fn();
vi.mock("../../hooks/useSetup", () => ({
  useCreatePlaythrough: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

vi.mock("../../hooks/useCreatePlaytest", () => ({
  useCreatePlaytest: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({ data: null, isLoading: false, isError: false }),
}));

vi.mock("../../hooks/useScenarioFocus", () => ({
  useScenarioFocus: () => ({
    scenario: {
      scenario_id: "strat-1",
      title: "Three Crowns War",
      mode: "strategy",
      genre_tags: ["strategy"],
      strategy_document: {
        factions: [
          {
            id: "valenreach",
            name: "Crown of Valenreach",
            color: "#46606E",
            is_playable: true,
            leader_id: "alden",
            treasury: 340,
            manpower: 14200,
            capital_seat: "Castle Highgard",
            government: "Feudal Monarchy",
          },
          {
            id: "oakhaven",
            name: "Duchy of Oakhaven",
            color: "#5E8A5A",
            is_playable: true,
            leader_id: "elena",
            treasury: 250,
            manpower: 8900,
            capital_seat: "Oakhaven Spire",
            government: "Duchy",
          },
        ],
        leaders: [
          {
            id: "alden",
            name: "King Alden IV",
            faction_id: "valenreach",
            epithet: "Sovereign of the Marches",
            portrait_url: "https://example.com/alden.png",
            trait_ids: ["cautious", "honorable"],
            ambition_ids: ["ambition_peace"],
            history: "Old king died and left the realm in peril.",
          },
          {
            id: "elena",
            name: "Duchess Elena",
            faction_id: "oakhaven",
            epithet: "Lady of the Green Weald",
            portrait_url: "https://example.com/elena.png",
            trait_ids: ["pragmatic", "cautious"],
            ambition_ids: ["ambition_peace"],
            history: "Elena governs the verdant woods.",
          },
        ],
        ambitions: [
          { id: "ambition_peace", name: "A stable peace", description: "Maintain realm tranquility" },
        ],
      },
    },
    isLoading: false,
    isError: false,
  }),
}));

describe("SetupPage Strategy Mode Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({ playthrough_id: "pt-strategy-100" });
  });

  it("renders StrategyRulerSetupScreen when scenario.mode is strategy", () => {
    renderWithClient(<SetupPage />);
    expect(screen.getByText(/Ruler Setup & Backstory/i)).toBeDefined();
    expect(screen.getByText(/Begin Reign Anno 1042/i)).toBeDefined();
    expect(screen.getByDisplayValue("King Alden IV")).toBeDefined();
  });

  it("switches factions and re-initializes ruler defaults", () => {
    renderWithClient(<SetupPage />);
    expect(screen.getByDisplayValue("King Alden IV")).toBeDefined();

    const oakhavenButton = screen.getByText("Duchy of Oakhaven");
    fireEvent.click(oakhavenButton);

    expect(screen.getByDisplayValue("Duchess Elena")).toBeDefined();
  });

  it("submits customized ruler and navigates to playthrough screen", async () => {
    renderWithClient(<SetupPage />);

    const nameInput = screen.getByDisplayValue("King Alden IV");
    fireEvent.change(nameInput, { target: { value: "High King Aurelius" } });

    const beginBtn = screen.getByText(/Begin Reign Anno 1042/i);
    fireEvent.click(beginBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          scenario_id: "strat-1",
          faction_id: "valenreach",
          player_ruler: expect.objectContaining({
            name: "High King Aurelius",
            epithet: "Sovereign of the Marches",
            trait_ids: ["cautious", "honorable"],
            ambition_ids: ["ambition_peace"],
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/play/pt-strategy-100");
    });
  });
});
