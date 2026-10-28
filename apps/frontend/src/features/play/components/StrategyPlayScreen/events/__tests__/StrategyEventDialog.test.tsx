import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyEventDialog } from "../StrategyEventDialog";
import type { StrategyEventPackage } from "../../../../types/eventScene.types";

describe("StrategyEventDialog", () => {
  it("renders manuscript event card and handles keyboard shortcuts", () => {
    const onSelectOption = vi.fn();
    const eventPackage: StrategyEventPackage = {
      sceneId: "scene-1",
      category: "trouble",
      title: "Trouble: The Harvest Fails at Ashford",
      subheading: "Ashford Bailey Jurisdiction",
      turnText: "Turn 48 • Autumn 1042",
      bodyProse: "An unseasonable black frost has scorched the rye before reaping.",
      causeQuote: "Because Lord Harl resents your taxes (opinion −40).",
      character: {
        name: "Lord Harl",
        title: "Castellan of Ashford",
        disposition: "Resentful",
      },
      choices: [
        {
          id: "opt-1",
          label: "Release Emergency Crown Grain Reserves",
          effects: ["Gold −50", "Unrest −4"],
        },
        {
          id: "opt-2",
          label: "Levy Tithe on Monasteries",
          effects: ["Church Opinion −15"],
        },
      ],
    };

    render(
      <StrategyEventDialog
        isOpen={true}
        eventPackage={eventPackage}
        onSelectOption={onSelectOption}
      />
    );

    expect(screen.getByText("Trouble: The Harvest Fails at Ashford")).toBeDefined();
    expect(screen.getByText("Lord Harl")).toBeDefined();

    // Test keyboard shortcut '1'
    fireEvent.keyDown(window, { key: "1" });
    expect(onSelectOption).toHaveBeenCalledWith("opt-1");
  });

  it("handles good news category and clicking on choices", () => {
    const onSelectOption = vi.fn();
    const onClose = vi.fn();
    const eventPackage: StrategyEventPackage = {
      sceneId: "scene-2",
      category: "good_news",
      title: "Good News: The Great Autumn Bumper Harvest",
      subheading: "Greenford Fluvial Plain",
      turnText: "Turn 48 • Autumn 1042",
      bodyProse: "The valley ditches held the late summer rain.",
      causeQuote: "Because you funded the granaries.",
      character: {
        name: "Lady Eleanor",
        title: "Master of Granaries",
        disposition: "Elated",
      },
      choices: [
        {
          id: "opt-b1",
          label: "Store Surplus into Royal Vaults",
          effects: ["Gold +80", "Stability +3"],
        },
      ],
    };

    render(
      <StrategyEventDialog
        isOpen={true}
        eventPackage={eventPackage}
        onSelectOption={onSelectOption}
        onClose={onClose}
      />
    );

    expect(screen.getByText("Good News: The Great Autumn Bumper Harvest")).toBeDefined();
    expect(screen.getByText("Lady Eleanor")).toBeDefined();
    expect(screen.getByText("Good News")).toBeDefined();

    const choiceButton = screen.getByRole("button", { name: /Store Surplus into Royal Vaults/i });
    fireEvent.click(choiceButton);
    expect(onSelectOption).toHaveBeenCalledWith("opt-b1");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("renders nothing when isOpen is false or eventPackage is null", () => {
    const { container, rerender } = render(
      <StrategyEventDialog
        isOpen={false}
        eventPackage={null}
        onSelectOption={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();

    rerender(
      <StrategyEventDialog
        isOpen={true}
        eventPackage={null}
        onSelectOption={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });
});
