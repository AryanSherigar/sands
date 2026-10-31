import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { buildScenarioFixture } from "../../test/studioApiMock";
import { renderGuideStep } from "../../test/renderGuideStep";
import { CombatEncounterEditor } from "./CombatEncounterEditor";
describe("combat encounter creator", () => {
    it("saves creator-defined values without replacing other rules", async () => {
        server.use(http.get("*/v1/scenarios/:scenarioId/maps", () => HttpResponse.json({ items: [] })));
        const { api, user } = await renderGuideStep(<CombatEncounterEditor />, {
            scenario: buildScenarioFixture({ mode: "master", genre_tags: ["High Fantasy"], rules: { text: "Keep this rule" }, state_schema: { ready: { type: "boolean", label: "Ready", initial: false } } }),
        });
        await user.click(screen.getByRole("button", { name: "Add combat encounter" }));
        await user.type(screen.getByLabelText("Encounter title"), "Road ambush");
        await user.selectOptions(screen.getByLabelText("Available when this value is yes"), "ready");
        for (const label of ["Player", "Opponent"]) {
            const group = within(screen.getByRole("group", { name: label }));
            for (const [field, value] of [["Starting health", "12"], ["Maximum health", "20"], ["Attack", "6"], ["Armor", "2"], ["Speed", "4"], ["Accuracy (0–100)", "75"], ["Luck (0–100)", "10"]]) {
                await user.type(group.getByLabelText(field), value);
            }
        }
        await user.type(screen.getByLabelText("Player health after defeat"), "4");
        await user.click(screen.getByRole("button", { name: "Add encounter" }));
        await waitFor(() => expect(api.scenario?.rules.fantasy_combat).toBeDefined(), { timeout: 4000 });
        expect(api.scenario?.rules.text).toBe("Keep this rule");
        expect(api.scenario?.rules.fantasy_combat).toMatchObject({ encounters: [{ title: "Road ambush", start_condition: { field: "ready", value: true }, player: { health: 12 }, fallback_outcome_id: "recovery" }] });
        expect(api.scenario?.state_schema.player.fields?.health.initial).toBe(12);
        await waitFor(() => expect(screen.getByText("Road ambush")).toBeInTheDocument());
        await user.click(screen.getByRole("button", { name: "Edit" }));
        const title = screen.getByLabelText("Encounter title");
        await user.clear(title);
        await user.type(title, "Bridge ambush");
        await user.click(screen.getByRole("button", { name: "Save encounter" }));
        await waitFor(() => expect(api.scenario?.rules.fantasy_combat).toMatchObject({ encounters: [{ title: "Bridge ambush" }] }), { timeout: 4000 });
    });
});
