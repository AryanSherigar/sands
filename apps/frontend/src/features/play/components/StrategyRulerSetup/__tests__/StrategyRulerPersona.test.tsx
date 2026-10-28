import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StrategyRulerPersona } from "../StrategyRulerPersona";

describe("StrategyRulerPersona", () => {
  const defaultRuler = {
    name: "King Alden IV",
    epithet: "Sovereign of the Marches",
    portraitUrl: "https://example.com/alden.png",
    traitIds: ["honorable", "cautious", "disciplined_steward"],
    ambitionIds: ["ambition_peace"],
    backstory: "Crowned in autumn.",
  };

  it("renders sovereign identity fields, trait cards, and opens trait drawer", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    render(
      <StrategyRulerPersona
        ruler={defaultRuler}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={false}
        availableTraits={[]}
        availableAmbitions={[]}
      />
    );
    expect(screen.getByDisplayValue("King Alden IV")).toBeDefined();
    expect(screen.getByText(/Redraft Backstory with AI/i)).toBeDefined();

    fireEvent.click(screen.getByText(/Change Virtues/i));
    expect(screen.getByText(/Choose Sovereign Virtues/i)).toBeDefined();
  });

  it("calls onUpdateRuler when name or epithet changes", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    render(
      <StrategyRulerPersona
        ruler={defaultRuler}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={false}
        availableTraits={[]}
        availableAmbitions={[]}
      />
    );

    const nameInput = screen.getByDisplayValue("King Alden IV");
    fireEvent.change(nameInput, { target: { value: "Queen Lyanna" } });
    expect(onUpdateRuler).toHaveBeenCalledWith({ name: "Queen Lyanna" });

    const epithetInput = screen.getByDisplayValue("Sovereign of the Marches");
    fireEvent.change(epithetInput, { target: { value: "The Shield of the North" } });
    expect(onUpdateRuler).toHaveBeenCalledWith({ epithet: "The Shield of the North" });
  });

  it("calls onRedraftBackstory when AI button is clicked", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    render(
      <StrategyRulerPersona
        ruler={defaultRuler}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={false}
        availableTraits={[]}
        availableAmbitions={[]}
      />
    );

    const redraftButton = screen.getByRole("button", { name: /Redraft Backstory with AI/i });
    fireEvent.click(redraftButton);
    expect(onRedraftBackstory).toHaveBeenCalledTimes(1);
  });

  it("disables redraft button and textarea during redrafting", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    render(
      <StrategyRulerPersona
        ruler={defaultRuler}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={true}
        availableTraits={[]}
        availableAmbitions={[]}
      />
    );

    expect(screen.getByText(/Inscribing with Chronicler.../i)).toBeDefined();
    const textarea = screen.getByDisplayValue("Crowned in autumn.");
    expect(textarea).toHaveProperty("disabled", true);
  });

  it("opens ambition drawer and toggles ambition", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    render(
      <StrategyRulerPersona
        ruler={defaultRuler}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={false}
        availableTraits={[]}
        availableAmbitions={[]}
      />
    );

    fireEvent.click(screen.getByText(/Change Ambition/i));
    expect(screen.getByText(/Choose Coronation Ambitions/i)).toBeDefined();

    // Click another ambition to add it
    const granaryAmbition = screen.getByText("The Great Granary");
    fireEvent.click(granaryAmbition);
    expect(onUpdateRuler).toHaveBeenCalledWith({
      ambitionIds: ["ambition_peace", "ambition_granary"],
    });
  });

  it("allows selecting and deselecting traits within the drawer", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    render(
      <StrategyRulerPersona
        ruler={{
          ...defaultRuler,
          traitIds: ["honorable", "cautious"],
        }}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={false}
        availableTraits={[]}
        availableAmbitions={[]}
      />
    );

    fireEvent.click(screen.getByText(/Change Virtues/i));
    expect(screen.getByText(/Choose Sovereign Virtues/i)).toBeDefined();

    // Select a 3rd trait "Wrathful"
    const wrathfulOption = screen.getByText("Wrathful");
    fireEvent.click(wrathfulOption);
    expect(onUpdateRuler).toHaveBeenCalledWith({
      traitIds: ["honorable", "cautious", "wrathful"],
    });
  });

  it("triggers onResetDefault and onBeginReign when action buttons are provided", () => {
    const onUpdateRuler = vi.fn();
    const onRedraftBackstory = vi.fn();
    const onResetDefault = vi.fn();
    const onBeginReign = vi.fn();

    render(
      <StrategyRulerPersona
        ruler={defaultRuler}
        onUpdateRuler={onUpdateRuler}
        onRedraftBackstory={onRedraftBackstory}
        isRedrafting={false}
        availableTraits={[]}
        availableAmbitions={[]}
        onResetDefault={onResetDefault}
        onBeginReign={onBeginReign}
      />
    );

    fireEvent.click(screen.getByText(/Restore Default Ruler/i));
    expect(onResetDefault).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText(/Begin Reign Anno 1042/i));
    expect(onBeginReign).toHaveBeenCalledTimes(1);
  });
});
