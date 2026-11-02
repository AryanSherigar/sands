import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CommanderDuelCards } from "../CommanderDuelCards";

describe("CommanderDuelCards", () => {
  it("renders player and enemy commanders with traits and mood badges", () => {
    render(
      <CommanderDuelCards
        playerCommander={{
          name: "Lord Aldric Vane",
          mood: "Calm",
          traits: ["Cautious (+5% Def)", "Veteran Warden"],
        }}
        enemyCommander={{
          name: "Warlord Brand",
          mood: "Fierce",
          traits: ["Fierce Charger (+15% Shock)"],
        }}
      />,
    );

    expect(screen.getByText("Lord Aldric Vane")).toBeInTheDocument();
    expect(screen.getByText("Calm")).toBeInTheDocument();
    expect(screen.getByText("Cautious (+5% Def)")).toBeInTheDocument();
    expect(screen.getByText("Warlord Brand")).toBeInTheDocument();
    expect(screen.getByText("Fierce")).toBeInTheDocument();
  });
});
