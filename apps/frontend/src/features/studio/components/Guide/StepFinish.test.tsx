import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
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
const FINISH_STEP = 7;
const READY = {
  title: "The Door Below",
  logline: "A lighthouse keeper finds a door in the sea.",
  opening_scene: "The tide is out.",
};
const SCENARIO_BASE = `*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}`;

const publishButton = (): HTMLElement =>
  within(screen.getByRole("region", { name: "Ready to share your story?" })).getByRole("button", {
    name: "Publish",
  });

const openFinish = async (init: Parameters<typeof installStudioApi>[0] = {}) => {
  const api = installStudioApi({ scenario: buildScenarioFixture(READY), ...init });
  const view = renderStudio({ path: EDIT_PATH });
  await screen.findByRole("tab", { name: "Guide" });
  act(() => useStudioTabsStore.getState().setGuideStep(FINISH_STEP));
  await screen.findByRole("heading", { name: "Ready to share your story?" });
  return { api, ...view };
};

const installPublishApi = (
  api: ReturnType<typeof installStudioApi>,
  respond?: () => Response,
) => {
  const calls = { publish: 0 };
  server.use(
    http.post(`${SCENARIO_BASE}/publish`, () => {
      calls.publish += 1;
      if (respond) return respond();
      api.scenario = { ...api.scenario!, status: "published", published_at: "2026-10-27T10:00:00Z" };
      return HttpResponse.json(api.scenario);
    }),
  );
  return calls;
};

const installAchievements = (responses: Array<Array<{ key: string; earned_at: string | null }>>) => {
  let index = 0;
  server.use(
    http.get("*/v1/users/me/achievements", () => {
      const current = responses[Math.min(index, responses.length - 1)];
      index += 1;
      return HttpResponse.json(
        current.map((item) => ({ name: "Worldmaker", requirement: "Publish your first story", ...item })),
      );
    }),
  );
};

describe("Step 7 Finish", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    installAchievements([[{ key: "worldmaker", earned_at: null }]]);
  });

  describe("preview, cover, access and content", () => {
    it("previews the card with the typographic cover when there is no cover image", async () => {
      await openFinish({ scenario: buildScenarioFixture({ ...READY, genre_tags: ["Mystery"] }) });
      const preview = screen.getByRole("article", { name: "How your story will look" });
      expect(within(preview).getByRole("img", { name: "The Door Below" })).toBeInTheDocument();
      expect(within(preview).getByText("A lighthouse keeper finds a door in the sea.")).toBeInTheDocument();
      expect(screen.getByText("No cover? We'll use this title cover.")).toBeInTheDocument();
    });

    it("shows the uploaded cover image in the preview instead", async () => {
      await openFinish({
        scenario: buildScenarioFixture({ ...READY, cover_image_url: "https://img.test/cover.png" }),
      });
      const preview = screen.getByRole("article", { name: "How your story will look" });
      expect(within(preview).queryByRole("img", { name: "The Door Below" })).toBeNull();
      expect(preview.querySelector("img")).toHaveAttribute("src", "https://img.test/cover.png");
    });

    it("defaults to Only people I invite and saves Everyone when chosen", async () => {
      const { api } = await openFinish();
      const user = userEvent.setup();
      expect(screen.getByLabelText("Only people I invite")).toBeChecked();
      await user.click(screen.getByLabelText("Everyone"));

      await waitFor(() => expect(api.scenarioUpdates.at(-1)).toMatchObject({ visibility: "public" }), WAIT);
    });

    it("starts the content warning at All Ages and never blocks publishing on it", async () => {
      await openFinish();
      expect(screen.getByText("Content warnings")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "All Ages" }).className).toContain("bg-content");
      expect(publishButton()).toBeEnabled();
    });
  });

  describe("checklist and Publish gating", () => {
    it("disables Publish and names exactly what is missing", async () => {
      await openFinish({ scenario: buildScenarioFixture() });
      expect(publishButton()).toBeDisabled();
      expect(screen.getByText("To publish, add: Name, One line idea, Opening.")).toBeInTheDocument();
      const required = screen.getByRole("list", { name: "Required" });
      expect(within(required).getAllByText("missing", { selector: ".sr-only" })).toHaveLength(3);
    });

    it("names only the opening when the rest is done and lets Fix jump to step 6", async () => {
      await openFinish({ scenario: buildScenarioFixture({ title: "T", logline: "L" }) });
      expect(screen.getByText("To publish, add: Opening.")).toBeInTheDocument();
      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "Fix Opening" }));
      expect(await screen.findByRole("heading", { name: "Where does the story begin?" })).toBeInTheDocument();
    });

    it("enables Publish once Name, One line idea and Opening exist", async () => {
      await openFinish();
      expect(publishButton()).toBeEnabled();
      expect(screen.queryByText(/To publish, add/)).toBeNull();
    });

    it("lists quiet suggestions with Fix links that never block", async () => {
      await openFinish();
      const user = userEvent.setup();
      expect(screen.getByText("Premise — add one for a richer story")).toBeInTheDocument();
      expect(screen.getByText("Characters — add someone for the player to meet")).toBeInTheDocument();
      expect(publishButton()).toBeEnabled();
      await user.click(screen.getByRole("button", { name: "Fix Premise" }));
      expect(await screen.findByRole("heading", { name: "Tell us about your story, the stakes." })).toBeInTheDocument();
    });

    it("marks a suggestion done once the story has it", async () => {
      await openFinish({
        entities: [buildEntityFixture({ entity_id: "c1", canonical_name: "Mara" })],
      });
      await waitFor(() => expect(screen.queryByText(/Characters — add/)).toBeNull());
    });

    it("opens the Playtest tab split right from Playtest first", async () => {
      await openFinish();
      await userEvent.setup().click(screen.getByRole("button", { name: "Playtest first" }));
      expect(useStudioTabsStore.getState().splitTabId).toBe("playtest");
    });
  });

  describe("publishing", () => {
    it("saves the default content tag, publishes and says only invited people can play", async () => {
      const { api } = await openFinish();
      const calls = installPublishApi(api);
      await userEvent.setup().click(publishButton());

      expect(
        await screen.findByText("Your story is published. Only people you invite can play it.", undefined, WAIT),
      ).toBeInTheDocument();
      expect(calls.publish).toBe(1);
      expect(api.scenarioUpdates.some((update) => update.content_tag === "all-ages")).toBe(true);
    });

    it("says the story is live when it is public", async () => {
      const { api } = await openFinish({
        scenario: buildScenarioFixture({ ...READY, visibility: "public" }),
      });
      installPublishApi(api);
      await userEvent.setup().click(publishButton());

      expect(await screen.findByText("Your story is live.", undefined, WAIT)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Make it public" })).toBeNull();
    });

    it("shows the failure in plain words with Try again, and tries again", async () => {
      const { api } = await openFinish();
      let shouldFail = true;
      const calls = installPublishApi(api, () => {
        if (!shouldFail) {
          api.scenario = { ...api.scenario!, status: "published" };
          return HttpResponse.json(api.scenario);
        }
        return HttpResponse.json({ detail: "The memory service is unavailable." }, { status: 503 });
      });
      const user = userEvent.setup();
      await user.click(publishButton());

      const alert = await screen.findByRole("alert", undefined, WAIT);
      expect(alert).toHaveTextContent("The memory service is unavailable.");
      shouldFail = false;
      await user.click(screen.getByRole("button", { name: "Try again" }));
      expect(await screen.findByText(/Your story is published/, undefined, WAIT)).toBeInTheDocument();
      expect(calls.publish).toBe(2);
    });

    it("does not publish when the pre-publish save failed, and publishes once the save works", async () => {
      const { api } = await openFinish();
      const calls = installPublishApi(api);
      let shouldSaveFail = true;
      server.use(
        http.patch(SCENARIO_BASE, () => {
          if (shouldSaveFail) return HttpResponse.json({ detail: "boom" }, { status: 500 });
          return HttpResponse.json(api.scenario);
        }),
      );
      const user = userEvent.setup();
      await user.click(publishButton());

      const alert = await screen.findByRole("alert", undefined, WAIT);
      expect(alert).toHaveTextContent("We couldn't save your latest changes");
      expect(calls.publish).toBe(0);

      shouldSaveFail = false;
      await user.click(screen.getByRole("button", { name: "Try again" }));
      expect(await screen.findByText(/Your story is published/, undefined, WAIT)).toBeInTheDocument();
      expect(calls.publish).toBe(1);
    });

    it("reveals the Worldmaker achievement after the first publish", async () => {
      installAchievements([
        [{ key: "worldmaker", earned_at: null }],
        [{ key: "worldmaker", earned_at: "2026-10-27T10:00:01Z" }],
      ]);
      const { api } = await openFinish();
      installPublishApi(api);
      await userEvent.setup().click(publishButton());

      expect(await screen.findByText("Achievement unlocked: Worldmaker", undefined, WAIT)).toBeInTheDocument();
      expect(screen.getByText("Publish your first story")).toBeInTheDocument();
    });

    it("does not reveal it again when it was already earned", async () => {
      installAchievements([[{ key: "worldmaker", earned_at: "2026-10-27T10:00:00Z" }]]);
      const { api } = await openFinish();
      installPublishApi(api);
      await userEvent.setup().click(publishButton());

      await screen.findByText(/Your story is published/, undefined, WAIT);
      expect(screen.queryByText(/Achievement unlocked/)).toBeNull();
    });
  });

  describe("after publishing", () => {
    const publishFirst = async (init: Parameters<typeof installStudioApi>[0] = {}) => {
      const view = await openFinish(init);
      installPublishApi(view.api);
      const user = userEvent.setup();
      await user.click(publishButton());
      await screen.findByText(/Your story is (published|live)/, undefined, WAIT);
      return { ...view, user };
    };

    it("offers Play it, Copy link, Invite people, Make it public and Back to Studio", async () => {
      await publishFirst();
      expect(screen.getByRole("link", { name: "Play it" })).toHaveAttribute("href", `/setup/${STUDIO_TEST_SCENARIO_ID}`);
      expect(screen.getByRole("button", { name: "Copy link" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Invite people" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Make it public" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Back to Studio" })).toHaveAttribute("href", "/studio");
    });

    it("copies the story page link", async () => {
      const { user } = await publishFirst();
      await user.click(screen.getByRole("button", { name: "Copy link" }));

      expect(await screen.findByText("Link copied")).toBeInTheDocument();
      expect(await navigator.clipboard.readText()).toBe(
        `${window.location.origin}/scenario/${STUDIO_TEST_SCENARIO_ID}`,
      );
    });

    it("makes the story public and updates the message", async () => {
      const { api, user } = await publishFirst();
      await user.click(screen.getByRole("button", { name: "Make it public" }));

      expect(await screen.findByText("Your story is live.", undefined, WAIT)).toBeInTheDocument();
      expect(api.scenarioUpdates.some((update) => update.visibility === "public")).toBe(true);
    });

    it("says plainly when making the story public could not be saved", async () => {
      const { api, user } = await publishFirst();
      server.use(http.patch(SCENARIO_BASE, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
      await user.click(screen.getByRole("button", { name: "Make it public" }));

      expect(await screen.findByText("We couldn't make your story public. Try again.", undefined, WAIT)).toBeInTheDocument();
      expect(screen.queryByText("Your story is live.")).toBeNull();
      expect(api.scenario?.visibility).not.toBe("public");
    });

    it("creates a single-use invite link, copies it and lists and removes people", async () => {
      let members = [{ user_id: "user-9", display_name: "Wren" }];
      const removed: string[] = [];
      server.use(
        http.get(`${SCENARIO_BASE}/access`, () => HttpResponse.json(members)),
        http.post(`${SCENARIO_BASE}/invites`, () =>
          HttpResponse.json({ url: "https://sands.test/invite/abc123", expires_at: "2026-10-27T10:00:00Z" }, { status: 201 }),
        ),
        http.delete(`${SCENARIO_BASE}/access/:userId`, ({ params }) => {
          removed.push(String(params.userId));
          members = [];
          return new HttpResponse(null, { status: 204 });
        }),
      );
      const { user } = await publishFirst();

      expect(await screen.findByText("Wren")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Invite people" }));
      expect(await screen.findByLabelText("Invite link")).toHaveValue("https://sands.test/invite/abc123");
      await user.click(screen.getByRole("button", { name: "Copy invite link" }));
      expect(await navigator.clipboard.readText()).toBe("https://sands.test/invite/abc123");

      await user.click(screen.getByRole("button", { name: "Remove Wren" }));
      await waitFor(() => expect(removed).toEqual(["user-9"]), WAIT);
      await waitFor(() => expect(screen.queryByText("Wren")).toBeNull(), WAIT);
    });

    it("says plainly when the invite link could not be made", async () => {
      server.use(
        http.post(`${SCENARIO_BASE}/invites`, () => HttpResponse.json({ detail: "nope" }, { status: 500 })),
      );
      const { user } = await publishFirst();
      await user.click(screen.getByRole("button", { name: "Invite people" }));

      expect(await screen.findByText("nope", undefined, WAIT)).toBeInTheDocument();
    });
  });

  describe("people on the Finish step", () => {
    it("lists who can play and removes someone before publishing", async () => {
      let members = [{ user_id: "user-9", display_name: "Wren" }];
      const removed: string[] = [];
      server.use(
        http.get(`${SCENARIO_BASE}/access`, () => HttpResponse.json(members)),
        http.delete(`${SCENARIO_BASE}/access/:userId`, ({ params }) => {
          removed.push(String(params.userId));
          members = [];
          return new HttpResponse(null, { status: 204 });
        }),
      );
      await openFinish();
      const user = userEvent.setup();
      const list = await screen.findByRole("list", { name: "People who can play" });
      expect(within(list).getByText("Wren")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Remove Wren" }));

      await waitFor(() => expect(removed).toEqual(["user-9"]), WAIT);
    });

    it("hides the invite tools when the story is for everyone", async () => {
      await openFinish({ scenario: buildScenarioFixture({ ...READY, visibility: "public" }) });
      expect(screen.queryByRole("button", { name: "Invite people" })).toBeNull();
    });
  });
});
