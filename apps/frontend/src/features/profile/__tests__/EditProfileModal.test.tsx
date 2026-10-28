import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { EditProfileModal } from "../components/EditProfileModal";
import type { UserProfile } from "../types/profile.types";

const profile: UserProfile = {
  user_id: "u-1",
  display_name: "Elminster",
  bio: "Archmage",
  avatar_url: null,
  banner_url: null,
  created_at: "2026-10-27T00:00:00Z",
  stats: {
    campaigns_played_count: 0,
    victories_count: 0,
    total_turns_taken: 0,
    scenarios_authored_count: 0,
    total_plays_received: 0,
  },
};

const renderModal = (isOpen: boolean, onClose = vi.fn()) =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <EditProfileModal profile={profile} isOpen={isOpen} onClose={onClose} />
    </QueryClientProvider>,
  );

describe("EditProfileModal", () => {
  it("renders nothing when closed", () => {
    renderModal(false);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders a dialog with the current name and bio and a Save action", () => {
    renderModal(true);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Elminster")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Archmage")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /save/i }),
    ).toBeInTheDocument();
  });

  it("closes via Cancel", () => {
    const handleClose = vi.fn();
    renderModal(true, handleClose);
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(handleClose).toHaveBeenCalled();
  });

  it("blocks saving an empty display name with an inline error", async () => {
    renderModal(true);
    fireEvent.change(screen.getByDisplayValue("Elminster"), {
      target: { value: "  " },
    });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(
      await screen.findByText("Display name cannot be empty."),
    ).toBeInTheDocument();
  });

  it("saves trimmed values and closes", async () => {
    let body: unknown = null;
    server.use(
      http.patch("*/v1/users/me", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(profile);
      }),
    );
    const handleClose = vi.fn();
    renderModal(true, handleClose);
    fireEvent.change(screen.getByDisplayValue("Elminster"), {
      target: { value: " Mystra " },
    });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(handleClose).toHaveBeenCalled());
    expect(body).toMatchObject({ display_name: "Mystra", bio: "Archmage" });
  });

  it("clears a failed-upload error after a successful retry", async () => {
    let attempt = 0;
    server.use(
      http.post("*/v1/uploads/avatar", () => {
        attempt += 1;
        return attempt === 1
          ? new HttpResponse(null, { status: 500 })
          : HttpResponse.json({ url: "/avatars/new.webp" });
      }),
    );
    renderModal(true);
    fireEvent.click(screen.getByRole("radio", { name: "Avatar" }));
    const input = screen.getByLabelText(/Upload a portrait/);
    const file = new File(["x"], "a.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Failed to upload avatar/,
    );
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });
});
