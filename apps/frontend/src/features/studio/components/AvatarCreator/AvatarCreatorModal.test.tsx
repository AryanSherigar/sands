import { useEffect } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { AvatarCreatorModal } from "./AvatarCreatorModal";

vi.mock("@/shared/components/AnimatedPortrait/AnimatedPortrait", () => ({
  AnimatedPortrait: ({ avatarUrl, onLoad }: { avatarUrl: string; onLoad?: () => void }) => {
    useEffect(() => {
      onLoad?.();
    }, [onLoad]);
    return <div data-testid="mesh-avatar" data-src={avatarUrl} />;
  },
}));

const PORTRAIT_URL = "https://cdn.test/leader-portraits/character.webp";

const PREMADE_AVATARS = [
  {
    id: "mira",
    name: "Mira",
    style: "Anime",
    avatar_url: "https://cdn.test/premade-avatars/mira.mavatar",
    preview_url: "https://cdn.test/premade-avatars/mira.webp",
    credit: "Miko © Yuki Shindo (AITuber OnAir)",
  },
  {
    id: "mei",
    name: "Mei",
    style: "Anime",
    avatar_url: "https://cdn.test/premade-avatars/mei.mavatar",
    preview_url: "https://cdn.test/premade-avatars/mei.webp",
    credit: null,
  },
];

function renderCharacterModal(onSave = vi.fn()) {
  server.use(
    http.get("*/v1/studio/avatars/premade", () => HttpResponse.json({ avatars: PREMADE_AVATARS })),
    http.post("*/v1/studio/avatars/optimize-prompt", () =>
      HttpResponse.json({ optimized_prompt: "Front-facing bust of a good looking woman" }),
    ),
    http.post("*/v1/studio/avatars/generate-portrait", () =>
      HttpResponse.json({ image_url: PORTRAIT_URL }),
    ),
  );
  render(
    <AvatarCreatorModal
      isOpen
      onClose={vi.fn()}
      characterName="Mira"
      characterLabel="Mira"
      onSave={onSave}
    />,
    { wrapper: createQueryWrapper() },
  );
}

describe("AvatarCreatorModal for characters", () => {
  it("lets a character generate a portrait image to build the avatar from", async () => {
    renderCharacterModal();
    fireEvent.change(screen.getByPlaceholderText(/Stern elven queen/i), {
      target: { value: "good looking woman" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Prepare portrait prompt/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Generate Portrait/i }));

    const preview = await screen.findByRole("img", { name: /portrait preview/i });
    expect(preview).toHaveAttribute("src", PORTRAIT_URL);
    expect(screen.getByRole("button", { name: /Build avatar/i })).toBeEnabled();
    expect(screen.queryByRole("button", { name: /Use this portrait/i })).not.toBeInTheDocument();
  });

  it("sends an image data url to build-mesh even when storage serves octet-stream", async () => {
    const seen = vi.fn();
    server.use(
      http.get(PORTRAIT_URL, () => new HttpResponse(new Blob(["image"]), { headers: { "content-type": "application/octet-stream" } })),
      http.post("*/v1/studio/avatars/build-mesh", async ({ request }) => {
        seen(await request.json());
        return HttpResponse.json({ avatar_url: "https://cdn.test/avatars/one.mavatar", name: "Mira" });
      }),
    );
    renderCharacterModal();
    fireEvent.change(screen.getByPlaceholderText(/Stern elven queen/i), {
      target: { value: "good looking woman" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Prepare portrait prompt/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Generate Portrait/i }));
    await screen.findByRole("img", { name: /portrait preview/i });
    fireEvent.click(screen.getByRole("button", { name: /Build avatar/i }));

    await waitFor(() => expect(seen).toHaveBeenCalled());
    expect(seen.mock.calls[0][0].image_url).toMatch(/^data:image\/webp;base64,/);
  });

  it("lets a creator attach a premade avatar without generating anything", async () => {
    const onSave = vi.fn();
    renderCharacterModal(onSave);
    fireEvent.click(await screen.findByRole("button", { name: /Use premade avatar Mei/i }));

    expect(screen.getByTestId("mesh-avatar")).toHaveAttribute("data-src", PREMADE_AVATARS[1].avatar_url);
    fireEvent.click(screen.getByRole("button", { name: /Attach to character/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalledWith(PREMADE_AVATARS[1].avatar_url));
  });

  it("shows the credit only for the selected avatar that has one", async () => {
    renderCharacterModal();
    expect(screen.queryByText(/Yuki Shindo/i)).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: /Use premade avatar Mira/i }));
    expect(screen.getByText(/Yuki Shindo/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Use premade avatar Mei/i }));
    expect(screen.queryByText(/Yuki Shindo/i)).not.toBeInTheDocument();
  });
});
