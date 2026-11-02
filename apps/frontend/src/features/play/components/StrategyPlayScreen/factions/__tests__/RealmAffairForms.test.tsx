import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppeaseForm } from "../AppeaseForm";
import { DemandPlayForm } from "../DemandPlayForm";
import { SubsidizeForm } from "../SubsidizeForm";
import { VassalDemandForm } from "../VassalDemandForm";

describe("realm affair forms", () => {
  it("subsidize sends the chosen receiver, amount and turns", () => {
    const onSubmit = vi.fn();
    render(
      <SubsidizeForm factionId="me" warId="w1" receivers={[{ id: "ash", label: "Ashford" }, { id: "car", label: "Carrow" }]} onSubmit={onSubmit} onCancel={vi.fn()} />,
    );

    fireEvent.change(screen.getByLabelText("Who receives it"), { target: { value: "car" } });
    fireEvent.change(screen.getByLabelText("Gold each turn"), { target: { value: "40" } });
    fireEvent.click(screen.getByRole("button", { name: "Pay the subsidy" }));

    expect(onSubmit).toHaveBeenCalledWith({
      kind: "subsidize", faction_id: "me", target_faction_id: "car", war_id: "w1", amount_per_turn: 40, turns: 4,
    });
  });

  it("appease builds each offer kind and blocks a cession with no claimed region", () => {
    const onSubmit = vi.fn();
    render(
      <AppeaseForm factionId="me" members={[{ id: "ash", label: "Ashford" }]} claimedRegionsByMember={{ ash: [] }} onSubmit={onSubmit} onCancel={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Make the offer" }));
    expect(onSubmit).toHaveBeenCalledWith({ kind: "appease_coalition", faction_id: "me", member_id: "ash", offer: { kind: "gold", amount: 50 } });

    fireEvent.change(screen.getByLabelText("Offer"), { target: { value: "claim_cession" } });
    expect(screen.getByText("This member claims none of your regions.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Make the offer" })).toBeDisabled();
  });

  it("vassal demand needs an amount over the treaty share", () => {
    const onSubmit = vi.fn();
    render(<VassalDemandForm factionId="me" vassalageId="v1" tributePercent={20} levyPercent={10} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "20" } });
    expect(screen.getByRole("button", { name: "Send the demand" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "35" } });
    fireEvent.click(screen.getByRole("button", { name: "Send the demand" }));

    expect(onSubmit).toHaveBeenCalledWith({ kind: "demand_from_vassal", faction_id: "me", vassalage_id: "v1", demand_kind: "tribute", amount: 35 });
  });

  it("demand play needs at least one term and sends cession and gold terms from the target to the player", () => {
    const onSubmit = vi.fn();
    render(
      <DemandPlayForm factionId="me" targetFactionId="ash" targetName="Ashford" targetRegions={[{ id: "r1", label: "Greenford" }]} onSubmit={onSubmit} onCancel={vi.fn()} />,
    );

    expect(screen.getByRole("button", { name: "Send the demand" })).toBeDisabled();
    expect(screen.getByText(/opens a war/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Greenford" }));
    fireEvent.change(screen.getByLabelText("Gold to pay"), { target: { value: "80" } });
    fireEvent.click(screen.getByRole("button", { name: "Send the demand" }));

    expect(onSubmit).toHaveBeenCalledWith({
      kind: "diplomatic_play",
      faction_id: "me",
      target_faction_id: "ash",
      demands: [
        { kind: "cede_region", from_faction_id: "ash", to_faction_id: "me", region_id: "r1" },
        { kind: "pay_gold", payer_id: "ash", payee_id: "me", amount: 80 },
      ],
    });
  });

  it("closes on Escape", () => {
    const onCancel = vi.fn();
    render(<SubsidizeForm factionId="me" warId="w1" receivers={[]} onSubmit={vi.fn()} onCancel={onCancel} />);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
