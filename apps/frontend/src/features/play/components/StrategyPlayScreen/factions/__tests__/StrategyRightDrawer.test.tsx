import type React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrategyRightDrawer } from "../StrategyRightDrawer";

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
});
