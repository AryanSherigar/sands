import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DEFAULT_PREVIEW_WORLD } from "../../defaultPreviewWorld";
import { RealmAffairsSection } from "../RealmAffairsSection";

const WORLD = {
  ...DEFAULT_PREVIEW_WORLD,
  rivals: [{ faction_id: "ash", name: "House Ashford", relation: "peace", treasury_range: { low: 0, high: 1 }, manpower_range: { low: 0, high: 1 } }],
  alliances: [{ id: "al-1", partner_id: "ash", alliance_type: "full" as const, is_separate_peace_banned: false }],
  subsidies: [{ id: "s1", payer_id: DEFAULT_PREVIEW_WORLD.my_faction.id, receiver_id: "ash", war_id: "w1", amount_per_turn: 50, turns_left: 4 }],
};

describe("RealmAffairsSection", () => {
  it("renders nothing for a quiet realm", () => {
    const { container } = render(
      <RealmAffairsSection world={{ ...DEFAULT_PREVIEW_WORLD, alliances: [], subsidies: [], vassalages: [], coalitions: [], wars: [], own_prisoners: [], own_hostages: [], mobilization: null }} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("submits an unconfirmed action straight away", () => {
    const onSubmitOrder = vi.fn();
    render(<RealmAffairsSection world={WORLD} onSubmitOrder={onSubmitOrder} />);

    fireEvent.click(screen.getByRole("button", { name: "Cut subsidy" }));

    expect(onSubmitOrder).toHaveBeenCalledWith(expect.objectContaining({ kind: "cut_subsidy", subsidy_id: "s1" }));
  });

  it("asks before denouncing, and only submits on confirm", () => {
    const onSubmitOrder = vi.fn();
    render(<RealmAffairsSection world={WORLD} onSubmitOrder={onSubmitOrder} />);

    fireEvent.click(screen.getByRole("button", { name: "Denounce" }));
    expect(onSubmitOrder).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog", { name: "Denounce this alliance?" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Denounce" }).at(-1)!);
    expect(onSubmitOrder).toHaveBeenCalledWith(expect.objectContaining({ kind: "denounce_alliance", alliance_id: "al-1" }));
  });

  it("does nothing when the confirmation is cancelled", () => {
    const onSubmitOrder = vi.fn();
    render(<RealmAffairsSection world={WORLD} onSubmitOrder={onSubmitOrder} />);

    fireEvent.click(screen.getByRole("button", { name: "Denounce" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onSubmitOrder).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });
});
