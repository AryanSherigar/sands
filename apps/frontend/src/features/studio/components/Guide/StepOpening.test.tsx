import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { STYLE_CHIPS } from "../../constants/styleChips";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const WAIT = { timeout: 4000 };
const OPENING_STEP = 6;

const openOpeningStep = async (init: Parameters<typeof installStudioApi>[0] = {}) => {
  const api = installStudioApi({ scenario: buildScenarioFixture(), ...init });
  const view = renderStudio({ path: EDIT_PATH });
  await screen.findByRole("tab", { name: "Guide" });
  act(() => useStudioTabsStore.getState().setGuideStep(OPENING_STEP));
  await screen.findByRole("heading", { name: "Where does the story begin?" });
  return { api, ...view };
};

const lastWorldData = (api: ReturnType<typeof installStudioApi>) =>
  api.scenarioUpdates.at(-1)?.world_data as
    | { openingDocument?: { blocks: Array<{ text: string; label?: string }> } }
    | undefined;

describe("Step 6 Opening", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
  });

  it("shows the header, helper and a large Play your opening that waits for text", async () => {
    await openOpeningStep();
    expect(
      screen.getByText(
        "Describe the moment the story starts. The narrator writes the first scene from this.",
      ),
    ).toBeInTheDocument();
    const play = screen.getByRole("button", { name: /Play your opening/ });
    expect(play).toBeDisabled();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Opening scene"), "The tide is out.");
    expect(play).toBeEnabled();
  });

  it("saves the opening as an opening document and never renders the persona on the client", async () => {
    const { api } = await openOpeningStep();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Opening scene"), "The tide is out.");

    await waitFor(
      () => expect(lastWorldData(api)?.openingDocument?.blocks[0].text).toBe("The tide is out."),
      WAIT,
    );
    expect(api.scenarioUpdates.some((update) => "narrator_persona" in update)).toBe(false);
  });

  it("Insert player's name adds the token and shows it as a chip", async () => {
    const { api } = await openOpeningStep();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Opening scene"), "Welcome,");
    await user.click(screen.getByRole("button", { name: "Insert player's name" }));

    expect(screen.getByLabelText("Opening scene")).toHaveValue("Welcome, {player_name}");
    expect(screen.getByText("player's name", { selector: "[data-token-chip]" })).toBeInTheDocument();
    await waitFor(
      () => expect(lastWorldData(api)?.openingDocument?.blocks[0].text).toBe("Welcome, {player_name}"),
      WAIT,
    );
  });

  it("links a starting place as 'The story starts at' and flags it when the place is gone", async () => {
    const lighthouse = buildEntityFixture({
      entity_id: "place-1",
      canonical_name: "The Lighthouse",
      entity_type: "location",
    });
    const { api } = await openOpeningStep({ entities: [lighthouse] });
    const user = userEvent.setup();
    const picker = await screen.findByLabelText("Starts at");
    await waitFor(() => expect(within(picker).getByRole("option", { name: "The Lighthouse" })).toBeInTheDocument());
    await user.selectOptions(picker, "place-1");

    await waitFor(() => {
      const blocks = lastWorldData(api)?.openingDocument?.blocks ?? [];
      expect(blocks.some((block) => block.label === "The story starts at" && block.text === "The Lighthouse")).toBe(true);
    }, WAIT);
  });

  it("offers the six opening questions, with a character pick for who else is here", async () => {
    await openOpeningStep();
    const user = userEvent.setup();
    await user.click(
      within(screen.getByRole("region", { name: "Active tab" })).getAllByRole("button", { name: /Questions to Help/ })[0],
    );
    await user.click(screen.getByRole("button", { name: /The first moment/ }));

    for (const prompt of [
      "Where is the player, exactly?",
      "What just happened?",
      "What can they see, hear or smell right now?",
      "Who else is here?",
      "What demands their attention first?",
      "What does the player know and not know yet?",
    ]) {
      expect(screen.getByText(prompt)).toBeInTheDocument();
    }
  });

  it("shows the seven style chips and inserts editable ready-made wording", async () => {
    const { api } = await openOpeningStep();
    const user = userEvent.setup();
    expect(screen.getByRole("heading", { name: "How should the story be told?" })).toBeInTheDocument();
    expect(screen.getByText("This guides how the narrator writes, every turn.")).toBeInTheDocument();
    for (const chip of STYLE_CHIPS) {
      expect(screen.getByRole("button", { name: chip.label })).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "Cozy" }));
    const cozy = STYLE_CHIPS.find((chip) => chip.id === "cozy")!;
    expect(screen.getByLabelText("Cozy")).toHaveValue(cozy.wording);
    await waitFor(() => {
      const persona = api.scenarioUpdates.at(-1)?.narrator_persona_document as {
        blocks: Array<{ label: string; text: string }>;
      };
      expect(persona.blocks[0]).toMatchObject({ label: "Cozy", text: cozy.wording });
    }, WAIT);

    await user.click(screen.getByRole("button", { name: "Cozy" }));
    await waitFor(() => {
      const persona = api.scenarioUpdates.at(-1)?.narrator_persona_document as { blocks: unknown[] };
      expect(persona.blocks).toHaveLength(0);
    }, WAIT);
  });

  it("Play your opening opens the Playtest tab split to the right", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({ opening_scene: "The tide is out." }),
    });
    renderStudio({ path: EDIT_PATH });
    await screen.findByRole("tab", { name: "Guide" });
    act(() => useStudioTabsStore.getState().setGuideStep(OPENING_STEP));
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Opening scene"), "x");
    await user.click(screen.getByRole("button", { name: /Play your opening/ }));

    expect(useStudioTabsStore.getState().splitTabId).toBe("playtest");
    expect(useStudioTabsStore.getState().openTabIds).toContain("playtest");
  });

  describe("Advanced mode invitation on Next", () => {
    it("asks once, 'Not now' goes straight to Finish without saving anything", async () => {
      const { api } = await openOpeningStep();
      const user = userEvent.setup();
      const updatesBefore = api.scenarioUpdates.length;
      await user.click(screen.getByRole("button", { name: "Next" }));

      expect(await screen.findByText("Your story is playable now. Want to turn on Advanced mode?")).toBeInTheDocument();
      expect(screen.getByText("Endings, things to track, rules.")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Not now" }));

      expect(await screen.findByRole("heading", { name: "Ready to share your story?" })).toBeInTheDocument();
      expect(api.scenarioUpdates.length).toBe(updatesBefore);
    });
  });
});
