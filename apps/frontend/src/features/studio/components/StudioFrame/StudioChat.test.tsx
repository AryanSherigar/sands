import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import type { SSEHandlers } from "@/shared/lib/sse-client";
import { SCOPED_TAB_TEXT_MAX_CHARS } from "../../constants/scopedChat";
import { GUIDE_TAB_ID, STUDIO_TABS_STORAGE_PREFIX } from "../../constants/studioTabs";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { buildEntityFixture } from "../../test/cardApiMock";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

interface CapturedRequest {
  url: string;
  body: Record<string, unknown>;
  handlers: SSEHandlers;
}

const requests: CapturedRequest[] = [];

vi.mock("@/shared/lib/sse-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/shared/lib/sse-client")>()),
  createPostSSEConnection: (
    url: string,
    body: Record<string, unknown>,
    _token: string | null,
    handlers: SSEHandlers,
  ) => {
    requests.push({ url, body, handlers });
    return vi.fn();
  },
}));

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const WAIT = { timeout: 4000 };
const mara = buildEntityFixture({
  entity_id: "mara",
  canonical_name: "Mara",
  lore_document: { blocks: [{ kind: "text", text: "Keeps the light." }] },
});
const DOOR_SCENARIO = buildScenarioFixture({ title: "The Door Below", logline: "A keeper hears knocking." });

const openChat = async (user: ReturnType<typeof userEvent.setup>): Promise<void> => {
  await user.click(await screen.findByRole("button", { name: "Chat" }));
};

const sendMessage = async (
  user: ReturnType<typeof userEvent.setup>,
  text: string,
): Promise<CapturedRequest> => {
  const before = requests.length;
  await user.type(screen.getByPlaceholderText("Ask about this tab..."), `${text}{Enter}`);
  await waitFor(() => expect(requests.length).toBe(before + 1));
  return requests[requests.length - 1];
};

const replyWith = (request: CapturedRequest, text: string): void => {
  request.handlers.onEvent("chunk", text);
  request.handlers.onEvent("done", "");
};

const setViewport = (isWide: boolean): void => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: isWide && query.includes("min-width: 1280px"),
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
};

describe("Studio scoped Chat", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(
      `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
      JSON.stringify({ openTabIds: [GUIDE_TAB_ID], activeTabId: GUIDE_TAB_ID, splitTabId: null, guideStep: 1 }),
    );
    requests.length = 0;
    useStudioTabsStore.getState().resetTabs();
    useStudioTabsStore.getState().setChatOpen(false);
    useStudioStore.getState().setHasEditConflict(false);
    useAuthStore.setState({
      user: { user_id: "user-1", display_name: "Creator", onboarding_completed: true },
      accessToken: "token",
      isAuthenticated: true,
    });
    // @ts-expect-error jsdom has no matchMedia unless a test installs one
    delete window.matchMedia;
  });

  it("says what Chat sees and follows the active tab", async () => {
    installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();

    await openChat(user);
    expect(await screen.findByText("Chat sees: Guide · Idea + your one line idea.")).toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: "Mara" }));
    expect(await screen.findByText("Chat sees: Mara + your one line idea.")).toBeInTheDocument();
  });

  it("sends only the active tab's text and the one line idea", async () => {
    installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await screen.findByText("Chat sees: Guide · Idea + your one line idea.");

    const request = await sendMessage(user, "Help me");

    expect(request.url).toContain("/v1/studio/assistant");
    expect(request.body.mode).toBe("scoped");
    expect(request.body).not.toHaveProperty("draft_context");
    expect(request.body.scoped_context).toEqual({
      one_line_idea: "A keeper hears knocking.",
      tab_kind: "guide",
      tab_label: "Guide · Idea",
      tab_text: expect.stringContaining("Name: The Door Below"),
    });
  });

  it("still sends the idea when the open tab is empty, and says so", async () => {
    installStudioApi({ scenario: buildScenarioFixture({ logline: "A keeper hears knocking." }) });
    localStorage.setItem(
      `${STUDIO_TABS_STORAGE_PREFIX}${STUDIO_TEST_SCENARIO_ID}`,
      JSON.stringify({ openTabIds: [GUIDE_TAB_ID], activeTabId: GUIDE_TAB_ID, splitTabId: null, guideStep: 2 }),
    );
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);

    expect(await screen.findByText("This tab is empty, so Chat only sees your one line idea.")).toBeInTheDocument();
    const request = await sendMessage(user, "Where do I start?");
    expect(request.body.scoped_context).toMatchObject({
      one_line_idea: "A keeper hears knocking.",
      tab_text: "",
    });
  });

  it("clamps very long tab text before sending it", async () => {
    const longLore = "x".repeat(SCOPED_TAB_TEXT_MAX_CHARS + 2000);
    installStudioApi({
      scenario: DOOR_SCENARIO,
      entities: [
        buildEntityFixture({
          entity_id: "mara",
          canonical_name: "Mara",
          lore_document: { blocks: [{ kind: "text", text: longLore }] },
        }),
      ],
    });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await screen.findByText("Chat sees: Mara + your one line idea.");

    const request = await sendMessage(user, "Tighten this");
    const context = request.body.scoped_context as { tab_text: string };
    expect(context.tab_text).toHaveLength(SCOPED_TAB_TEXT_MAX_CHARS);
  });

  it("applies nothing until Accept, then writes only the open step's field", async () => {
    const api = installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await screen.findByText("Chat sees: Guide · Idea + your one line idea.");

    const request = await sendMessage(user, "A better name?");
    replyWith(request, "Try this:\n```action:title\nThe Door Above\n```");

    const card = await screen.findByText(/Suggested change · Name/);
    expect(within(card.parentElement as HTMLElement).getByText("The Door Below")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect(api.scenarioUpdates).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => expect(api.scenarioUpdates).toHaveLength(1), WAIT);
    expect(api.scenarioUpdates[0]).toMatchObject({ title: "The Door Above" });
    expect(Object.keys(api.scenarioUpdates[0]).filter((key) => key !== "expected_content_edited_at")).toEqual(["title"]);
    expect(await screen.findByRole("button", { name: "Accepted" })).toBeDisabled();
  });

  it("keeps Accept off for a suggestion that belongs to another tab", async () => {
    const api = installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await screen.findByText("Chat sees: Guide · Idea + your one line idea.");

    const request = await sendMessage(user, "Describe the world");
    replyWith(request, "```action:lore\nA drowned coast.\n```");

    expect(await screen.findByText("Open the World step or a card to accept this.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept" })).toBeDisabled();
    expect(api.scenarioUpdates).toHaveLength(0);
  });

  it("writes a suggestion into the open card through the guarded update", async () => {
    const api = installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await screen.findByText("Chat sees: Mara + your one line idea.");

    const request = await sendMessage(user, "Give her a secret");
    replyWith(request, '```action:story_card {"type":"Character","name":"Mara"}\nShe hides a key.\n```');
    await user.click(await screen.findByRole("button", { name: "Accept" }));

    await waitFor(() => expect(api.entityUpdates).toHaveLength(1), WAIT);
    expect(api.entityUpdates[0].entityId).toBe("mara");
    expect(api.entityUpdates[0].body.lore_document).toEqual({
      blocks: [{ kind: "text", text: "She hides a key." }],
    });
    expect(api.scenarioUpdates).toHaveLength(0);
  });

  it("asks before overwriting a field that changed since the suggestion", async () => {
    const api = installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await screen.findByText("Chat sees: Guide · Idea + your one line idea.");

    const request = await sendMessage(user, "A better name?");
    replyWith(request, "```action:title\nThe Door Above\n```");
    await screen.findByRole("button", { name: "Accept" });

    const name = screen.getByLabelText("Story name");
    await user.clear(name);
    await user.type(name, "Changed meanwhile");
    await waitFor(() => expect(api.scenarioUpdates.length).toBeGreaterThan(0), WAIT);
    await new Promise((resolve) => setTimeout(resolve, 300));

    await user.click(screen.getByRole("button", { name: "Accept" }));
    expect(await screen.findByText("Field Conflict Detected")).toBeInTheDocument();
    const updatesBefore = api.scenarioUpdates.length;
    await user.click(screen.getByRole("button", { name: "Replace Existing" }));
    await waitFor(() => expect(api.scenarioUpdates.length).toBe(updatesBefore + 1), WAIT);
    expect(api.scenarioUpdates[updatesBefore]).toMatchObject({ title: "The Door Above" });
  });

  it("dismisses a suggestion without writing", async () => {
    const api = installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await screen.findByText("Chat sees: Guide · Idea + your one line idea.");

    replyWith(await sendMessage(user, "Name?"), "```action:title\nNope\n```");
    await user.click(await screen.findByRole("button", { name: "Dismiss" }));

    expect(await screen.findByText("Dismissed: Name")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).toBeNull();
    expect(api.scenarioUpdates).toHaveLength(0);
  });

  it("keeps one history per story and clears it with New chat", async () => {
    installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await openChat(user);
    await screen.findByText("Chat sees: Guide · Idea + your one line idea.");
    await sendMessage(user, "Remember this question");
    await user.click(screen.getByRole("button", { name: "Mara" }));

    expect(screen.getByText("Remember this question")).toBeInTheDocument();
    expect(
      localStorage.getItem(`sands_studio_assistant_chat:scoped:user-1:${STUDIO_TEST_SCENARIO_ID}`),
    ).toContain("Remember this question");

    await user.click(screen.getByRole("button", { name: "New chat" }));
    expect(screen.queryByText("Remember this question")).toBeNull();
  });

  it("becomes a third column on a wide screen and overlays the split below 1280px", async () => {
    installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    setViewport(true);
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await user.click(screen.getByRole("button", { name: "Tab options for Mara" }));
    await user.click(screen.getByRole("menuitem", { name: "Split right" }));
    await openChat(user);

    const chat = await screen.findByRole("complementary", { name: "Chat" });
    expect(chat.className).not.toContain("absolute");
    expect(screen.getByRole("region", { name: "Split tab" })).toBeInTheDocument();
  });

  it("overlays the split when the screen is narrower than 1280px", async () => {
    installStudioApi({ scenario: DOOR_SCENARIO, entities: [mara] });
    setViewport(false);
    renderStudio({ path: EDIT_PATH });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Mara" }));
    await user.click(screen.getByRole("button", { name: "Tab options for Mara" }));
    await user.click(screen.getByRole("menuitem", { name: "Split right" }));
    await openChat(user);

    expect((await screen.findByRole("complementary", { name: "Chat" })).className).toContain("absolute");
  });
});
