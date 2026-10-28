import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { NAME_SETUP_FIELD } from "../../constants/guideChips";
import { getGuideSteps } from "../../lib/guideStepsFor";
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

const getActiveTab = (): HTMLElement => screen.getByRole("region", { name: "Active tab" });

const goToStep = (stepNumber: number): void => {
  act(() => useStudioTabsStore.getState().setGuideStep(stepNumber));
};

const withName = buildScenarioFixture({ setup_schema: [NAME_SETUP_FIELD] });

const openStep = async (stepNumber: number, init: Parameters<typeof installStudioApi>[0] = {}) => {
  const api = installStudioApi({ scenario: buildScenarioFixture(), ...init });
  const view = renderStudio({ path: EDIT_PATH });
  await screen.findByRole("tab", { name: "Guide" });
  goToStep(stepNumber);
  return { api, ...view };
};

describe("Guide steps", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
  });

  describe("step bar and frame", () => {
    it("shows Back, Step N of 7, the step name and Skip to full editor", async () => {
      await openStep(3);
      const bar = await screen.findByRole("navigation", { name: "Guide steps" });
      expect(within(bar).getByRole("button", { name: "Back" })).toBeInTheDocument();
      expect(within(bar).getByText("Step 3 of 7")).toBeInTheDocument();
      expect(within(bar).getByText("Player")).toBeInTheDocument();
      expect(within(bar).getByRole("button", { name: "Skip to full editor" })).toBeInTheDocument();
    });

    it("has no Back on step 1 and Next is always enabled", async () => {
      await openStep(1);
      const bar = await screen.findByRole("navigation", { name: "Guide steps" });
      expect(within(bar).queryByRole("button", { name: "Back" })).toBeNull();
      expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
    });

    it("moves with Next and Back and never gets stuck on an empty step", async () => {
      await openStep(1);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "Next" }));
      expect(await screen.findByRole("heading", { name: "Tell us about your story, the stakes." })).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Back" }));
      expect(await screen.findByRole("heading", { name: "What's your story in one sentence?" })).toBeInTheDocument();
    });

    it("shows every step's exact header and helper", async () => {
      await openStep(1);
      for (const step of getGuideSteps(false)) {
        goToStep(step.number);
        expect(await screen.findByRole("heading", { name: step.header })).toBeInTheDocument();
        if (step.helper) expect(screen.getByText(step.helper)).toBeInTheDocument();
      }
    });

    it("has no Next on the last step", async () => {
      await openStep(7);
      expect(await screen.findByRole("heading", { name: "Ready to share your story?" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Next" })).toBeNull();
    });

    it("skips to a one-page editor view with every section and returns to the first unfinished step", async () => {
      await openStep(2, { scenario: buildScenarioFixture({ title: "T", logline: "L" }) });
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "Skip to full editor" }));

      expect(await screen.findByRole("heading", { name: "Who will the player be?" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Tell us about your world." })).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Open Guide" }));
      expect(await screen.findByRole("heading", { name: "Tell us about your story, the stakes." })).toBeInTheDocument();
    });

    it("folds an example away until asked", async () => {
      await openStep(1);
      const user = userEvent.setup();
      expect(screen.queryByRole("complementary", { name: "Example" })).toBeNull();
      await user.click(await screen.findByRole("button", { name: "Show an example" }));
      expect(screen.getByRole("complementary", { name: "Example" })).toHaveTextContent("The Door Below");
    });
  });

  describe("Step 1 Idea", () => {
    it("has a one line idea with counter and helper, a name with its hint, and no Questions to Help", async () => {
      await openStep(1);
      const idea = await screen.findByLabelText("One line idea");
      expect(idea).toHaveAttribute("placeholder", "A lighthouse keeper finds a door in the sea.");
      expect(screen.getByText("This shows on your story's card.")).toBeInTheDocument();
      expect(screen.getByText("0 / 150")).toBeInTheDocument();
      expect(screen.getByText("No rush — you can name it later.")).toBeInTheDocument();
      expect(within(getActiveTab()).queryByText("Questions to Help")).toBeNull();
    });

    it("counts characters and saves the idea and the name", async () => {
      const { api } = await openStep(1);
      const user = userEvent.setup();
      await user.type(await screen.findByLabelText("One line idea"), "A door");
      expect(screen.getByText("6 / 150")).toBeInTheDocument();
      await user.type(screen.getByLabelText("What is the name of the story?"), "The Door");

      await waitFor(
        () => expect(api.scenarioUpdates.at(-1)).toMatchObject({ logline: "A door", title: "The Door" }),
        WAIT,
      );
    });

    it("stops the name at 64 characters", async () => {
      await openStep(1);
      const user = userEvent.setup();
      const name = await screen.findByLabelText("What is the name of the story?");
      await user.click(name);
      await user.paste("n".repeat(100));
      expect(name).toHaveValue("n".repeat(64));
      expect(screen.getByText("64 / 64")).toBeInTheDocument();
    });
  });

  describe("Step 2 Premise", () => {
    it("echoes the saved idea above a lore box with a soft word guide and the three questions", async () => {
      await openStep(2, { scenario: buildScenarioFixture({ logline: "A door in the sea" }) });
      expect(await screen.findByText("Your idea · Saved: “A door in the sea”")).toBeInTheDocument();
      expect(screen.getByText("Aim for 50–150 words")).toBeInTheDocument();

      const user = userEvent.setup();
      await user.click(within(getActiveTab()).getByRole("button", { name: /Questions to Help/ }));
      await user.click(screen.getByRole("button", { name: /Your story/ }));
      expect(screen.getByText("What do they want?")).toBeInTheDocument();
      expect(screen.getByText("What stands in their way?")).toBeInTheDocument();
      expect(screen.getByText("What happens if they fail?")).toBeInTheDocument();
    });

    it("never blocks on word count and saves the premise document", async () => {
      const { api } = await openStep(2);
      const user = userEvent.setup();
      await user.type(await screen.findByLabelText("Your story and the stakes"), "Short");

      await waitFor(() => {
        const world = api.scenarioUpdates.at(-1)?.world_data as { premiseDocument?: { blocks: Array<{ text: string }> } };
        expect(world?.premiseDocument?.blocks[0].text).toBe("Short");
      }, WAIT);
      expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
    });

    it("marks the first genre picked as Primary and promotes the next when it is removed", async () => {
      const { api } = await openStep(2);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "Mystery" }));
      await user.click(screen.getByRole("button", { name: "Horror" }));

      expect(screen.getByRole("button", { name: /Mystery\s*Primary/ })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Horror" })).toHaveAttribute("aria-pressed", "true");
      await waitFor(() => expect(api.scenarioUpdates.at(-1)).toMatchObject({ genre_tags: ["Mystery", "Horror"] }), WAIT);

      await user.click(screen.getByRole("button", { name: /Mystery/ }));
      expect(screen.getByRole("button", { name: /Horror\s*Primary/ })).toBeInTheDocument();
    });

    it("offers mood chips and accepts your own", async () => {
      const { api } = await openStep(2);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "eerie" }));
      await user.type(screen.getByLabelText("Add your own feeling"), "salty{Enter}");

      expect(screen.getByRole("button", { name: "salty" })).toHaveAttribute("aria-pressed", "true");
      await waitFor(() => expect(api.scenarioUpdates.at(-1)).toMatchObject({ mood_tags: ["eerie", "salty"] }), WAIT);
      for (const mood of ["cozy", "tense", "funny", "epic", "sad"]) {
        expect(screen.getByRole("button", { name: mood })).toBeInTheDocument();
      }
    });
  });

  describe("Step 3 Player", () => {
    it("lets the creator choose a written player or one the player creates", async () => {
      const { api } = await openStep(3);
      const user = userEvent.setup();
      expect(await screen.findByLabelText("A character I write")).toBeChecked();
      await user.click(screen.getByLabelText("Someone the player creates"));

      await waitFor(() => expect(api.scenarioUpdates.at(-1)).toMatchObject({ player_mode: "player_created" }), WAIT);
    });

    it("creates the player card as is_player and shows its questions", async () => {
      const { api } = await openStep(3);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "Describe the player" }));

      await waitFor(() => expect(api.entities).toHaveLength(1), WAIT);
      expect(api.entities[0]).toMatchObject({ is_player: true, entity_type: "character" });
      const card = await screen.findByRole("article");
      await user.click(within(card).getByRole("button", { name: /Questions to Help/ }));
      await user.click(within(card).getByRole("button", { name: /About the player/ }));
      for (const prompt of ["Looks", "Background", "What are they good at?", "What do they want?", "What do they carry?", "What don't they know yet?"]) {
        expect(within(card).getAllByText(prompt).length).toBeGreaterThan(0);
      }
    });

    it("starts a new story with the Name setup field and offers the quick-add chips", async () => {
      installStudioApi();
      renderStudio({ path: "/studio/new" });
      await screen.findByRole("tab", { name: "Guide" });
      goToStep(3);
      expect(await screen.findByDisplayValue("Name")).toBeInTheDocument();
      for (const chip of ["+ Pronouns", "+ Looks", "+ Background", "+ Starting item", "+ Difficulty", "+ Your own…"]) {
        expect(screen.getByRole("button", { name: chip })).toBeInTheDocument();
      }
    });

    it("adds Difficulty with Gentle, Normal and Harsh and saves the setup", async () => {
      const { api } = await openStep(3, { scenario: withName });
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "+ Difficulty" }));

      expect(screen.getByDisplayValue("Gentle")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Normal")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Harsh")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "+ Difficulty" })).toBeNull();
      await waitFor(() => {
        const schema = api.scenarioUpdates.at(-1)?.setup_schema as Array<{ label: string }>;
        expect(schema.map((field) => field.label)).toContain("Difficulty");
      }, WAIT);
    });

    it("adds your own question and can remove it again, plain type names only", async () => {
      await openStep(3, { scenario: withName });
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "+ Your own…" }));
      const typeSelect = screen.getAllByRole("combobox")[1];
      expect(within(typeSelect).getAllByRole("option").map((option) => option.textContent)).toEqual([
        "Short answer",
        "Long answer",
        "Number",
        "Pick one",
        "Pick several",
      ]);
      await user.click(screen.getByRole("button", { name: "Remove this question" }));
      expect(screen.queryAllByLabelText("Question label")).toHaveLength(1);
    });

    it("previews the Setup screen", async () => {
      await openStep(3, { scenario: withName });
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "Preview the Setup screen" }));
      expect(within(screen.getByRole("region", { name: "Setup screen preview" })).getByText("Name")).toBeInTheDocument();
    });
  });

  describe("Step 4 Characters", () => {
    it("is fine with zero characters and adds one with + Add character", async () => {
      const { api } = await openStep(4);
      const user = userEvent.setup();
      expect(screen.queryByRole("article")).toBeNull();
      await user.click(await screen.findByRole("button", { name: "+ Add character" }));

      await waitFor(() => expect(api.entities).toHaveLength(1), WAIT);
      expect(api.entities[0]).toMatchObject({ entity_type: "character" });
      expect(await screen.findByRole("article")).toBeInTheDocument();
    });

    it("has nine question groups, one open at a time, with an answered counter", async () => {
      await openStep(4, { entities: [buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" })] });
      const user = userEvent.setup();
      const card = within(await screen.findByRole("article"));
      await user.click(card.getByRole("button", { name: /Questions to Help/ }));
      expect(card.getByText(/0 of \d+ answered/)).toBeInTheDocument();

      const groups = ["Looks", "Personality", "Voice", "Wants & fears", "With the player", "History", "What they know", "Where", "How they change"];
      for (const name of groups) {
        expect(card.getByRole("button", { name: new RegExp(`^${name.replace("&", "&")}`) })).toBeInTheDocument();
      }
      await user.click(card.getByRole("button", { name: /^Looks/ }));
      await user.click(card.getByRole("button", { name: /^Voice/ }));
      expect(card.queryByText("How old are they?")).toBeNull();
      expect(card.getByText("How do they talk?")).toBeInTheDocument();
    });
  });

  describe("Step 5 World", () => {
    it("shows the world lore box with its eight question groups and no word guide", async () => {
      await openStep(5);
      const user = userEvent.setup();
      expect(await screen.findByLabelText("Your world")).toBeInTheDocument();
      expect(screen.queryByText(/Aim for/)).toBeNull();
      await user.click(within(getActiveTab()).getByRole("button", { name: /Questions to Help/ }));
      for (const name of ["Time & place", "Everyday life", "Power", "Danger", "Special rules", "History", "Senses & mood", "Secrets"]) {
        expect(screen.getByRole("button", { name: new RegExp(`^${name}`) })).toBeInTheDocument();
      }
    });

    it("keeps an Always remember list with an N of 10 counter and a nudge at 10 that does not block", async () => {
      const lines = Array.from({ length: 9 }, (_, index) => `Rule ${index + 1}`);
      const { api } = await openStep(5, {
        scenario: buildScenarioFixture({ world_data: { alwaysRemember: lines } }),
      });
      const user = userEvent.setup();
      expect(await screen.findByText("9 of 10")).toBeInTheDocument();
      expect(screen.queryByText(/Keep the list short/)).toBeNull();

      await user.click(screen.getByRole("button", { name: "+ Add" }));
      expect(screen.getByText("10 of 10")).toBeInTheDocument();
      expect(screen.getByText("Keep the list short — the narrator reads this every turn.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "+ Add" })).toBeEnabled();
      await user.type(screen.getByLabelText("Always remember 10"), "Never lie");

      await waitFor(() => {
        const world = api.scenarioUpdates.at(-1)?.world_data as { alwaysRemember: string[] };
        expect(world.alwaysRemember).toHaveLength(10);
        expect(world.alwaysRemember[9]).toBe("Never lie");
      }, WAIT);
    });

    it("adds place, group and thing cards with their own questions", async () => {
      const { api } = await openStep(5);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "+ Place" }));
      await user.click(await screen.findByRole("button", { name: "+ Group" }));
      await user.click(await screen.findByRole("button", { name: "+ Thing" }));

      await waitFor(() => expect(api.entities.map((entity) => entity.entity_type)).toEqual(["location", "faction", "item"]), WAIT);
      const cards = await screen.findAllByRole("article");
      expect(cards).toHaveLength(3);
      await user.click(within(cards[0]).getByRole("button", { name: /Questions to Help/ }));
      expect(within(cards[0]).getByRole("button", { name: /^Senses/ })).toBeInTheDocument();
      await user.click(within(cards[1]).getByRole("button", { name: /Questions to Help/ }));
      expect(within(cards[1]).getByRole("button", { name: /^Purpose/ })).toBeInTheDocument();
      await user.click(within(cards[2]).getByRole("button", { name: /Questions to Help/ }));
      expect(within(cards[2]).getByRole("button", { name: /^Ownership/ })).toBeInTheDocument();
    });

    it("creates the creator's custom type first, then the Other card", async () => {
      const { api } = await openStep(5);
      const user = userEvent.setup();
      await user.click(await screen.findByRole("button", { name: "+ Other" }));
      await user.type(await screen.findByLabelText(/Name the kind/), "Sea Creature");
      await user.click(screen.getByRole("button", { name: "Add" }));

      await waitFor(() => expect(api.entities).toHaveLength(1), WAIT);
      expect(api.entityTypeCreates).toEqual([
        expect.objectContaining({ type_key: "sea_creature", display_label: "Sea Creature" }),
      ]);
      expect(api.entities[0]).toMatchObject({ entity_type: "sea_creature" });
    });
  });
});
