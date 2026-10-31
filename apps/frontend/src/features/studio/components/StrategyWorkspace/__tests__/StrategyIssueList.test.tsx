import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyIssueList } from "../StrategyIssueList";

const issues = [
  { code: "faction_has_no_army", path: "factions[0]", message: "'ashford' has no army" },
  { code: "faction_has_no_region", path: "factions[1]", message: "'carrow' owns no region" },
];

describe("StrategyIssueList", () => {
  it("opens the matching panel from a mapped issue", () => {
    const onOpenPanel = vi.fn();
    render(<StrategyIssueList issues={issues} tone="text-danger" onOpenPanel={onOpenPanel} />);
    fireEvent.click(screen.getByRole("button", { name: "'ashford' has no army" }));
    expect(onOpenPanel).toHaveBeenCalledWith("armies");
  });

  it("renders an unmapped issue as plain text", () => {
    render(<StrategyIssueList issues={issues} tone="text-danger" onOpenPanel={vi.fn()} />);
    expect(screen.getByText("'carrow' owns no region")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "'carrow' owns no region" })).not.toBeInTheDocument();
  });
});
