import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderGuideStep } from "../../test/renderGuideStep";
import { buildScenarioFixture } from "../../test/studioApiMock";
import { SimplePortraitSchedule } from "./SimplePortraitSchedule";

describe("Simple scene changes", () => {
  it("saves a turn and character list without replacing other rules", async () => {
    const character = buildEntityFixture({ entity_id: "asha", canonical_name: "Asha", avatar_url: "https://example.com/a.mavatar" });
    const { api, user } = await renderGuideStep(<SimplePortraitSchedule characters={[character]} />, { scenario: buildScenarioFixture({ mode: "newbie", genre_tags: ["Slice of Life"], rules: { text: "Keep" } }) });
    await user.click(screen.getByRole("checkbox", { name: "Asha" }));
    await user.click(screen.getByRole("button", { name: "Save scene change" }));
    await waitFor(() => expect(api.scenario?.rules.portrait_schedule).toEqual([{ turn: 1, character_ids: ["asha"] }]), { timeout: 4000 });
    expect(api.scenario?.rules.text).toBe("Keep");
  });
});
