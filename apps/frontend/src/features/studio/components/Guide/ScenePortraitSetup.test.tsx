import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderGuideStep } from "../../test/renderGuideStep";
import { buildScenarioFixture } from "../../test/studioApiMock";
import { ScenePortraitSetup } from "./ScenePortraitSetup";

describe("scene portrait setup", () => {
  it("saves opening characters for Simple stories without altering other rules", async () => {
    const character = buildEntityFixture({ entity_id: "asha", canonical_name: "Asha", avatar_url: "https://example.com/a.mavatar" });
    const { api, user } = await renderGuideStep(<ScenePortraitSetup characters={[character]} />, {
      scenario: buildScenarioFixture({ mode: "newbie", genre_tags: ["Slice of Life"], rules: { text: "Keep" } }),
    });
    await user.click(screen.getByRole("checkbox", { name: "Asha" }));
    await waitFor(() => expect(api.scenario?.rules.portrait_opening_ids).toEqual(["asha"]), { timeout: 4000 });
    expect(api.scenario?.rules.text).toBe("Keep");
  });
  it("sets the initial scene using existing tracked state without replacing other fields", async () => {
    const character = buildEntityFixture({ entity_id: "asha", canonical_name: "Asha", avatar_url: "https://example.com/a.mavatar" });
    const { api, user } = await renderGuideStep(<ScenePortraitSetup characters={[character]} />, {
      scenario: buildScenarioFixture({ mode: "master", genre_tags: ["Slice of Life"], state_schema: { coins: { type: "number", initial: 5 } } }),
    });
    await user.click(screen.getByRole("checkbox", { name: "Asha" }));
    await waitFor(() => expect(api.scenario?.state_schema.scene_character_ids).toMatchObject({ type: "list", item_type: "entity_ref", initial: ["asha"] }), { timeout: 4000 });
    expect(api.scenario?.state_schema.coins.initial).toBe(5);
  });

  it("does not overwrite an incompatible existing field", async () => {
    const character = buildEntityFixture({ entity_id: "asha", canonical_name: "Asha", avatar_url: "https://example.com/a.mavatar" });
    await renderGuideStep(<ScenePortraitSetup characters={[character]} />, {
      scenario: buildScenarioFixture({ mode: "master", genre_tags: ["Slice of Life"], state_schema: { scene_character_ids: { type: "string", initial: "secret" } } }),
    });
    expect(screen.getByText(/incompatible configuration/i)).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "Asha" })).not.toBeInTheDocument();
  });
});
