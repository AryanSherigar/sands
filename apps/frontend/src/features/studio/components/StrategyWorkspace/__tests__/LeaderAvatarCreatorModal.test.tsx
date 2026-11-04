import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { LeaderAvatarCreatorModal } from "../LeaderAvatarCreatorModal";
import { AvatarCreatorModal } from "../../AvatarCreator/AvatarCreatorModal";
import { useEffect } from "react";

vi.mock("@/shared/components/AnimatedPortrait/AnimatedPortrait", () => ({
  AnimatedPortrait: ({ onLoad }: { onLoad?: () => void }) => {
    useEffect(() => { onLoad?.(); }, [onLoad]);
    return null;
  },
}));

describe("avatar portrait selection", () => {
  beforeEach(() => {
    server.use(http.get("*/v1/studio/avatars/premade", () => HttpResponse.json({ avatars: [] })));
  });

  it("supports a story character without a faction", () => {
    render(<AvatarCreatorModal isOpen onClose={vi.fn()} characterName="Asha" characterLabel="Asha" onSave={vi.fn()} />, { wrapper: createQueryWrapper() });
    expect(screen.getByRole("dialog", { name: "Create animated character avatar" })).toBeInTheDocument();
    expect(screen.getByText("Create an animated 2D mesh avatar for Asha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attach to character" })).toBeDisabled();
  });

  it("keeps the dialog open when attaching the avatar fails", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<AvatarCreatorModal isOpen onClose={onClose} characterName="Asha" characterLabel="Asha" currentAvatarUrl="https://example.com/asha.mavatar" onSave={async () => { throw new Error("save failed"); }} />, { wrapper: createQueryWrapper() });
    await user.click(screen.getByRole("button", { name: "Attach to character" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not attach the avatar");
    expect(onClose).not.toHaveBeenCalled();
  });
  it("builds from the selected portrait and attaches the returned avatar", async () => {
    let imageUrl = "";
    server.use(http.post("*/v1/studio/avatars/build-mesh", async ({ request }) => {
      imageUrl = (await request.json() as { image_url: string }).image_url;
      return HttpResponse.json({ name: "Mira", avatar_url: "https://example.com/mira.mavatar" });
    }));
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<LeaderAvatarCreatorModal isOpen onClose={vi.fn()} leaderName="Mira" factionName="North" onSave={onSave} />, { wrapper: createQueryWrapper() });
    expect(screen.getByRole("button", { name: /build avatar/i })).toBeDisabled();
    await user.upload(screen.getByLabelText(/choose portrait/i), new File(["image"], "portrait.png", { type: "image/png" }));
    await user.click(screen.getByRole("button", { name: /build avatar/i }));
    await waitFor(() => expect(imageUrl).toMatch(/^data:image\/png;base64,/));
    await user.click(await screen.findByRole("button", { name: /attach to leader/i }));
    expect(onSave).toHaveBeenCalledWith("https://example.com/mira.mavatar");
  });

  it("shows a build error without attaching a sample avatar", async () => {
    server.use(http.post("*/v1/studio/avatars/build-mesh", () => HttpResponse.json({ detail: "Invalid image" }, { status: 422 })));
    const user = userEvent.setup();
    render(<LeaderAvatarCreatorModal isOpen onClose={vi.fn()} leaderName="Mira" factionName="North" onSave={vi.fn()} />, { wrapper: createQueryWrapper() });
    await user.upload(screen.getByLabelText(/choose portrait/i), new File(["bad"], "bad.png", { type: "image/png" }));
    await user.click(screen.getByRole("button", { name: /build avatar/i }));
    expect(await screen.findByText(/could not build the avatar/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /attach to leader/i })).toBeDisabled();
  });
});
