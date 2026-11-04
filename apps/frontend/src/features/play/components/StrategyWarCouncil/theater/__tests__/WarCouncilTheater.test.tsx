import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WarCouncilTheater } from "../WarCouncilTheater";

const wards = {
  left: { ward: "left", title: "Left Vanguard", stance: "hold", isAnchor: false, ranks: [] },
  center: { ward: "center", title: "Center Main Battle", stance: "hold", isAnchor: true, ranks: [] },
  right: { ward: "right", title: "Right Reargard", stance: "hold", isAnchor: false, ranks: [] },
} as const;

const props = {
  opponent: { faction_id: "rival", strength: { minimum: 10, maximum: 20 }, reports: [] },
  wards: wards as never,
  onUpdateCohortCount: vi.fn(),
  onReorderRank: vi.fn(),
  reservePolicy: "conserve" as const,
  onChangeReservePolicy: vi.fn(),
  canCommitReserves: false,
  onCommitReserves: vi.fn(),
  canScout: false,
  onOrderScout: vi.fn(),
};

describe("WarCouncilTheater", () => {
  it("collapses and reopens the planning sketch of wards", () => {
    render(<WarCouncilTheater {...props} activeTroops={{ infantry: 5 }} reserveTroops={{}} />);
    const toggle = screen.getByRole("button", { name: /Our Battle Array/ });

    expect(screen.getByText("Left Vanguard")).toBeInTheDocument();
    fireEvent.click(toggle);
    expect(screen.queryByText("Left Vanguard")).toBeNull();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("In the line")).toBeInTheDocument();

    fireEvent.click(toggle);
    expect(screen.getByText("Left Vanguard")).toBeInTheDocument();
  });
});
