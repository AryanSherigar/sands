import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { LeaderAvatarCreatorModal } from "../LeaderAvatarCreatorModal";

vi.mock("@/shared/components/AnimatedPortrait/AnimatedPortrait", () => ({
  AnimatedPortrait: ({ avatarUrl }: { avatarUrl: string }) => (
    <div data-testid="mesh-avatar" data-src={avatarUrl} />
  ),
}));

const PORTRAIT_URL = "https://cdn.test/leader-portraits/one.webp";
const AVATAR_URL = "https://cdn.test/avatars/one.mavatar";

function mockPortraitApi(portraits: string[] = [PORTRAIT_URL]) {
  const queue = [...portraits];
  server.use(
    http.get("*/v1/studio/avatars/premade", () => HttpResponse.json({ avatars: [] })),
    http.get("https://cdn.test/leader-portraits/:name", () => new HttpResponse(new Blob(["image"], { type: "image/webp" }))),
    http.post("*/v1/studio/avatars/optimize-prompt", () =>
      HttpResponse.json({ optimized_prompt: "Front-facing bust of a stern queen" }),
    ),
    http.post("*/v1/studio/avatars/generate-portrait", () =>
      HttpResponse.json({ image_url: queue.shift() ?? PORTRAIT_URL }),
    ),
  );
}

function renderModal(overrides: Partial<React.ComponentProps<typeof LeaderAvatarCreatorModal>> = {}) {
  const props = {
    isOpen: true,
    onClose: vi.fn(),
    leaderName: "Queen Mira",
    factionName: "Dunmere",
    currentAvatarUrl: null,
    currentPortraitUrl: null,
    onSave: vi.fn(),
    onSavePortrait: vi.fn(),
    ...overrides,
  };
  render(<LeaderAvatarCreatorModal {...props} />, { wrapper: createQueryWrapper() });
  return props;
}

async function generatePortrait() {
  fireEvent.change(screen.getByPlaceholderText(/Stern elven queen/i), {
    target: { value: "a stern queen" },
  });
  fireEvent.click(screen.getByRole("button", { name: /Prepare portrait prompt/i }));
  fireEvent.click(await screen.findByRole("button", { name: /Generate Portrait/i }));
  return screen.findByRole("img", { name: /portrait preview/i });
}

describe("LeaderAvatarCreatorModal portrait flow", () => {
  it("generates a portrait preview and saves it as the leader portrait", async () => {
    mockPortraitApi();
    const props = renderModal();
    const preview = await generatePortrait();
    expect(preview).toHaveAttribute("src", PORTRAIT_URL);
    fireEvent.click(screen.getByRole("button", { name: /Use this portrait/i }));
    expect(props.onSavePortrait).toHaveBeenCalledWith(PORTRAIT_URL);
  });

  it("disables rigging until a portrait exists", () => {
    mockPortraitApi();
    renderModal();
    expect(screen.getByRole("button", { name: /Build avatar/i })).toBeDisabled();
  });

  it("sends the saved portrait url to build-mesh", async () => {
    mockPortraitApi();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["image"], { type: "image/webp" }),
    } as Response);
    const seen = vi.fn();
    server.use(
      http.post("*/v1/studio/avatars/build-mesh", async ({ request }) => {
        seen(await request.json());
        return HttpResponse.json({ avatar_url: AVATAR_URL, name: "Queen Mira" });
      }),
    );
    renderModal();
    await generatePortrait();
    fireEvent.click(screen.getByRole("button", { name: /Build avatar/i }));
    await waitFor(() => expect(screen.getByTestId("mesh-avatar")).toHaveAttribute("data-src", AVATAR_URL));
    expect(seen).toHaveBeenCalledWith({ name: "Queen Mira", image_url: expect.stringMatching(/^data:image\/webp;base64,/) });
    fetchSpy.mockRestore();
  });

  it("shows an error and no stand-in avatar when portrait generation fails", async () => {
    server.use(
      http.post("*/v1/studio/avatars/optimize-prompt", () =>
        HttpResponse.json({ optimized_prompt: "Front-facing bust" }),
      ),
      http.post("*/v1/studio/avatars/generate-portrait", () =>
        HttpResponse.json({ detail: "bad" }, { status: 502 }),
      ),
    );
    renderModal();
    fireEvent.change(screen.getByPlaceholderText(/Stern elven queen/i), {
      target: { value: "a stern queen" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Prepare portrait prompt/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Generate Portrait/i }));
    expect(await screen.findByText(/could not generate a portrait/i)).toBeInTheDocument();
    expect(screen.queryByTestId("mesh-avatar")).toBeNull();
    expect(document.body.innerHTML).not.toContain("/avatars/mira.mavatar");
  });

  it("replaces the preview when regenerating", async () => {
    mockPortraitApi([PORTRAIT_URL, "https://cdn.test/leader-portraits/two.webp"]);
    renderModal();
    await generatePortrait();
    fireEvent.click(screen.getByRole("button", { name: /Regenerate Portrait/i }));
    await waitFor(() =>
      expect(screen.getByRole("img", { name: /portrait preview/i })).toHaveAttribute(
        "src",
        "https://cdn.test/leader-portraits/two.webp",
      ),
    );
  });
});
