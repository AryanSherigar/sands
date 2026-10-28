import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyEventDialog } from "../StrategyEventDialog";
import { buildPendingEventPackage } from "../../../../lib/pendingEventPackage";
import { makePendingEvent } from "../../../../test-utils/eventFixtures";
import type { StrategyEventPackage } from "../../../../types/eventScene.types";
import type { CampaignWorldView } from "../../../../types/simulation.types";

function packageFor(overrides = {}): StrategyEventPackage {
  const world = {
    turn: 5,
    clock: { turn: 5, start_year: 1042, start_month: 1 },
    pending_events: [makePendingEvent(overrides)],
  } as CampaignWorldView;
  return buildPendingEventPackage(world, "event_1") as StrategyEventPackage;
}

function renderDialog(eventPackage: StrategyEventPackage) {
  const props = { onSelectOption: vi.fn(), onCancelQueued: vi.fn(), onClose: vi.fn() };
  render(<StrategyEventDialog isOpen eventPackage={eventPackage} {...props} />);
  return props;
}

describe("StrategyEventDialog decisions", () => {
  it("shows each choice's order cost and effects", () => {
    renderDialog(packageFor());
    expect(screen.getByText("1 order")).toBeDefined();
    expect(screen.getByText("2 orders")).toBeDefined();
    expect(screen.getByText("Gold −20")).toBeDefined();
  });

  it("states what happens if the event is left unanswered", () => {
    renderDialog(packageFor());
    expect(
      screen.getByText("If you leave this unanswered: Unrest +10, Governor opinion −10"),
    ).toBeDefined();
  });

  it("answers by click and by number key", () => {
    const props = renderDialog(packageFor());
    fireEvent.click(screen.getByRole("button", { name: /Send troops to break the protest/ }));
    fireEvent.keyDown(window, { key: "1" });
    expect(props.onSelectOption).toHaveBeenNthCalledWith(1, "garrison_crackdown");
    expect(props.onSelectOption).toHaveBeenNthCalledWith(2, "ease_taxes");
  });

  it("blocks a choice the player cannot afford, by click and by key", () => {
    const event = makePendingEvent();
    event.choices[0].is_affordable = false;
    const world = {
      turn: 5,
      clock: { turn: 5, start_year: 1042, start_month: 1 },
      pending_events: [event],
    } as CampaignWorldView;
    const props = renderDialog(buildPendingEventPackage(world, "event_1") as StrategyEventPackage);
    const blocked = screen.getByRole("button", {
      name: /Lighten the levy in this region/,
    }) as HTMLButtonElement;
    expect(blocked.disabled).toBe(true);
    expect(screen.getByText("Can't afford")).toBeDefined();
    fireEvent.click(blocked);
    fireEvent.keyDown(window, { key: "1" });
    expect(props.onSelectOption).not.toHaveBeenCalled();
  });

  it("shows a queued answer, locks the other choices and offers to cancel it", () => {
    const props = renderDialog(
      packageFor({ queued_choice_id: "ease_taxes", queued_command_id: "cmd-9" }),
    );
    expect(screen.getByRole("status").textContent).toContain("Answer queued");
    expect(screen.getByText("Queued")).toBeDefined();
    fireEvent.keyDown(window, { key: "2" });
    expect(props.onSelectOption).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel answer" }));
    expect(props.onCancelQueued).toHaveBeenCalledWith("cmd-9");
  });

  it("keeps the scene-based shortfall dialog working without costs", () => {
    const shortfall: StrategyEventPackage = {
      sceneId: "scene-1",
      category: "trouble",
      title: "Trouble: Treasury Shortfall",
      subheading: "",
      turnText: "",
      bodyProse: "The treasury is empty.",
      causeQuote: "",
      character: { name: "Treasurer", title: "Exchequer", disposition: "Distressed" },
      choices: [{ id: "shortfall_take_loan", label: "Take a loan", effects: [] }],
    };
    const props = renderDialog(shortfall);
    expect(screen.queryByText(/order/i)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Take a loan/ }));
    expect(props.onSelectOption).toHaveBeenCalledWith("shortfall_take_loan");
  });
});
