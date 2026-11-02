import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KnownFactionRow } from "../KnownFactionRow";
import type { RivalView } from "../../../../types/simulation.types";

const RIVAL: RivalView = {
  faction_id: "house_ashford",
  name: "House Ashford",
  leader_name: "Lord Ashford",
  relation: "war",
  treasury_range: { low: 0, high: 10 },
  manpower_range: { low: 0, high: 10 },
};

describe("KnownFactionRow sue for peace", () => {
  it("sues for peace on the actual war id, not the rival id", () => {
    const handleOrder = vi.fn();
    render(
      <KnownFactionRow rival={RIVAL} warId="war-7" myFactionId="me" onSubmitOrder={handleOrder} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Sue for Peace" }));
    expect(handleOrder).toHaveBeenCalledWith({ kind: "sue_peace", faction_id: "me", war_id: "war-7" });
  });

  it("offers no sue-for-peace when no war record is known", () => {
    render(<KnownFactionRow rival={RIVAL} myFactionId="me" onSubmitOrder={vi.fn()} />);

    expect(screen.queryByRole("button", { name: "Sue for Peace" })).not.toBeInTheDocument();
  });
});
