import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyLeaderHistoryEditor } from "../StrategyLeaderHistoryEditor";
import * as strategyApi from "../../../api/strategy.api";

describe("StrategyLeaderHistoryEditor", () => {
  const leader = {
    id: "mira",
    name: "Queen Mira",
    faction_id: "dunmere",
    trait_ids: ["cautious", "proud"],
    ambition_ids: ["wealth"],
    history: "A cunning monarch of the Dunmere vales.",
    age: 32,
  };

  it("renders history label, textarea, and Draft button", () => {
    render(
      <StrategyLeaderHistoryEditor
        leader={leader}
        factionName="Dunmere"
        onEdit={vi.fn()}
      />,
    );

    expect(
      screen.getByLabelText("Leader history & backstory"),
    ).toHaveValue("A cunning monarch of the Dunmere vales.");
    expect(
      screen.getByRole("button", { name: "✦ Draft with Muse" }),
    ).toBeInTheDocument();
  });

  it("updates history on text edit", () => {
    const onEdit = vi.fn();
    render(
      <StrategyLeaderHistoryEditor
        leader={leader}
        factionName="Dunmere"
        onEdit={onEdit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Leader history & backstory"), {
      target: { value: "New chronicle text" },
    });
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("drafts history using AI and applies it", async () => {
    const onEdit = vi.fn();
    vi.spyOn(strategyApi, "draftRulerBackstory").mockResolvedValue(
      "Forged in iron and grief, Queen Mira ascended the high throne.",
    );

    render(
      <StrategyLeaderHistoryEditor
        leader={leader}
        factionName="Dunmere"
        onEdit={onEdit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "✦ Draft with Muse" }));

    await waitFor(() => {
      expect(strategyApi.draftRulerBackstory).toHaveBeenCalledWith({
        ruler_name: "Queen Mira",
        faction_id: "Dunmere",
        trait_ids: ["cautious", "proud"],
        ambition_ids: ["wealth"],
      });
      expect(onEdit).toHaveBeenCalledTimes(1);
    });
  });

  it("shows error alert when drafting fails", async () => {
    vi.spyOn(strategyApi, "draftRulerBackstory").mockRejectedValue(
      new Error("Network failed"),
    );

    render(
      <StrategyLeaderHistoryEditor
        leader={leader}
        factionName="Dunmere"
        onEdit={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "✦ Draft with Muse" }));

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Could not draft history");
  });
});
