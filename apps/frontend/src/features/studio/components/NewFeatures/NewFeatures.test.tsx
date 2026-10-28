import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NEW_FEATURES, type NewFeature } from "../../constants/newFeatures";
import { GuideScenarioProvider } from "../Guide/GuideScenarioProvider";
import { useNewFeaturesStore } from "../../stores/newFeatures.store";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";
import { NewFeatureTab } from "./NewFeatureTab";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const WAIT = { timeout: 4000 };
const OLD_STORY = "2026-10-27T00:00:00Z";
const NEW_STORY = "2026-11-02T10:00:00Z";
const mara = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });

const getFeaturesRegion = (): HTMLElement =>
  screen.getByRole("region", { name: "New features" });

const setReducedMotion = (isReduced: boolean): void => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: isReduced && query.includes("prefers-reduced-motion"),
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
};

const openFeature = async (
  user: ReturnType<typeof userEvent.setup>,
  name: string,
): Promise<void> => {
  await user.click(within(await screen.findByRole("region", { name: "New features" })).getByRole("button", { name }));
};

describe("New features", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    useNewFeaturesStore.getState().setUnseenFeatureIds([]);
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  it("lists the launch features for a story made before they shipped, with an unseen count", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ created_at: OLD_STORY }) });
    renderStudio({ path: EDIT_PATH });

    const region = await screen.findByRole("region", { name: "New features" });
    for (const name of ["Triggers", "Links", "Always remember", "Storytelling style", "Player step", "Questions to Help"]) {
      expect(within(region).getByRole("button", { name })).toBeInTheDocument();
    }
    expect(within(region).getByText(String(NEW_FEATURES.length))).toBeInTheDocument();
  });

  it("says nothing is new for a story made after the release", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ created_at: NEW_STORY }) });
    renderStudio({ path: EDIT_PATH });

    const region = await screen.findByRole("region", { name: "New features" });
    expect(within(region).getByText("Nothing new since you made this story.")).toBeInTheDocument();
    expect(within(region).getByText("0")).toBeInTheDocument();
  });

  it("opens an entry as a tab with its date, example and where to find it", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ created_at: OLD_STORY }) });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await openFeature(user, "Links");

    expect(await screen.findByRole("tab", { name: "Links" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("New · Oct 28, 2026")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Where to find it" })).toHaveTextContent("Open any card");
    expect(screen.getByRole("region", { name: "Example" })).toBeInTheDocument();
  });

  it("moves an entry to Seen on Got it and saves it for this story only", async () => {
    const api = installStudioApi({ scenario: buildScenarioFixture({ created_at: OLD_STORY }) });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await openFeature(user, "Links");
    await user.click(await screen.findByRole("button", { name: "Got it" }));

    await waitFor(() => expect(api.scenarioUpdates).toHaveLength(1), WAIT);
    expect(api.scenarioUpdates[0].guide_seen_features).toEqual(["links"]);
    const region = getFeaturesRegion();
    expect(within(region).getByText(String(NEW_FEATURES.length - 1))).toBeInTheDocument();
    expect(within(region).getByText("Seen (1)")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Got it" })).toBeNull();
  });

  it("reads seen state from the story when it opens", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({ created_at: OLD_STORY, guide_seen_features: ["links", "triggers"] }),
    });
    renderStudio({ path: EDIT_PATH });

    const region = await screen.findByRole("region", { name: "New features" });
    expect(within(region).getByText(String(NEW_FEATURES.length - 2))).toBeInTheDocument();
    expect(within(region).getByText("Seen (2)")).toBeInTheDocument();
  });

  it("tags a feature New in its own place until it is seen", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({ created_at: OLD_STORY, guide_seen_features: ["links"] }),
      entities: [mara],
    });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await screen.findByLabelText("Add a trigger");
    const triggers = document.querySelector('[data-feature-id="triggers"]') as HTMLElement;
    const links = document.querySelector('[data-feature-id="links"]') as HTMLElement;
    expect(within(triggers).getByText("New")).toBeInTheDocument();
    expect(within(links).queryByText("New")).toBeNull();
  });

  it("Show me opens the feature's real place and highlights it for 300ms", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ created_at: OLD_STORY }) });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await openFeature(user, "Always remember");
    await user.click(await screen.findByRole("button", { name: "Show me" }));

    expect(await screen.findByRole("heading", { name: "Tell us about your world." })).toBeInTheDocument();
    const anchor = document.querySelector('[data-feature-id="always-remember"]') as HTMLElement;
    expect(anchor).toHaveAttribute("data-highlighted", "true");
    await waitFor(() => expect(anchor).not.toHaveAttribute("data-highlighted"), { timeout: 1500 });
  });

  it("does not highlight under prefers-reduced-motion", async () => {
    setReducedMotion(true);
    installStudioApi({ scenario: buildScenarioFixture({ created_at: OLD_STORY }) });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await openFeature(user, "Always remember");
    await user.click(await screen.findByRole("button", { name: "Show me" }));

    await screen.findByRole("heading", { name: "Tell us about your world." });
    const anchor = document.querySelector('[data-feature-id="always-remember"]') as HTMLElement;
    expect(anchor).not.toHaveAttribute("data-highlighted");
  });

  it("opens a Guide story that was made before the redesign", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({
        created_at: "2026-10-27T00:00:00Z",
        title: "Old Story",
        logline: "Old idea",
        narrator_persona: "Be dramatic.",
        world_data: {
          mainConflict: "A war",
          worldLore: "Old lore",
          openingPrompt: "You wake.",
          storyCards: [{ id: "1", type: "Character", name: "Hero", content: "Brave" }],
        },
      }),
    });
    renderStudio({ path: EDIT_PATH });

    expect(await screen.findByRole("heading", { name: "What's your story in one sentence?" })).toBeInTheDocument();
    expect(screen.getByLabelText("One line idea")).toHaveValue("Old idea");
  });
});

const advancedFeature: NewFeature = {
  id: "future-advanced",
  name: "Future thing",
  description: "Only for advanced creators.",
  releasedOn: "2026-10-28",
  location: "In the Advanced editor.",
  example: "Example.",
  isAdvanced: true,
  target: { kind: "guide-step", stepNumber: 2 },
};

const renderFeatureTab = (isAdvancedOn: boolean) => {
  installStudioApi({ scenario: buildScenarioFixture({ created_at: OLD_STORY }) });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <GuideScenarioProvider scenarioId={STUDIO_TEST_SCENARIO_ID} onDraftCreated={() => undefined}>
          <NewFeatureTab feature={advancedFeature} isAdvancedOn={isAdvancedOn} />
        </GuideScenarioProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("Advanced-only feature entry", () => {
  beforeEach(() => {
    useStudioTabsStore.getState().resetTabs();
  });

  it("is labelled Advanced mode and offers the hint when Advanced is off", async () => {
    renderFeatureTab(false);
    const user = userEvent.setup();

    expect(await screen.findByText("Advanced mode")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show me" }));

    expect(screen.getByRole("status")).toHaveTextContent("Turn on Advanced mode to use this.");
    expect(useStudioTabsStore.getState().guideStep).toBe(1);
  });

  it("shows the feature when Advanced is on", async () => {
    renderFeatureTab(true);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Show me" }));

    expect(screen.queryByRole("status")).toBeNull();
    expect(useStudioTabsStore.getState().activeTabId).toBe("guide");
    expect(useStudioTabsStore.getState().guideStep).toBe(2);
  });
});
