import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProfileHeader } from "../components/ProfileHeader";
import { CampaignCard } from "../components/cards/CampaignCard";
import { UserReviewCard } from "../components/cards/UserReviewCard";
import {
  UserProfile,
  UserPlaythroughSummary,
  UserReviewSummary,
} from "../types/profile.types";

const mockProfile: UserProfile = {
  user_id: "user-123",
  display_name: "Elminster",
  bio: "Archmage of Shadowdale",
  avatar_url: "/avatars/mage.webp",
  banner_url: "/banners/portal.png",
  created_at: "2026-10-27T00:00:00Z",
  stats: {
    campaigns_played_count: 7,
    victories_count: 5,
    total_turns_taken: 84,
    scenarios_authored_count: 3,
    total_plays_received: 120,
  },
};

describe("ProfileComponents", () => {
  it("renders ProfileHeader with identity and an Edit profile button for the owner", () => {
    const handleEdit = vi.fn();
    render(
      <ProfileHeader
        profile={mockProfile}
        isOwner={true}
        onEditClick={handleEdit}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Elminster" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Archmage of Shadowdale")).toBeInTheDocument();
    expect(screen.getByText(/^Joined/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));
    expect(handleEdit).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Turns Taken")).toBeNull();
  });

  it("hides Edit profile when isOwner is false", () => {
    render(
      <ProfileHeader
        profile={mockProfile}
        isOwner={false}
        onEditClick={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Edit profile" })).toBeNull();
  });

  it("has no Settings link or role chip", () => {
    render(
      <ProfileHeader
        profile={mockProfile}
        isOwner={true}
        onEditClick={vi.fn()}
      />,
    );
    expect(screen.queryByText(/settings/i)).toBeNull();
    expect(screen.queryByText(/creator & chronicler/i)).toBeNull();
  });

  it("shows a fallback when there is no bio", () => {
    render(
      <ProfileHeader
        profile={{ ...mockProfile, bio: null }}
        isOwner={false}
        onEditClick={vi.fn()}
      />,
    );
    expect(screen.getByText("No bio yet.")).toBeInTheDocument();
  });

  it("offers More only for long bios and expands on click", () => {
    render(
      <ProfileHeader
        profile={{ ...mockProfile, bio: "x".repeat(400) }}
        isOwner={false}
        onEditClick={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByRole("button", { name: "Less" })).toBeInTheDocument();
  });

  it("offers More for a short bio with many lines and always clamps when collapsed", () => {
    render(
      <ProfileHeader
        profile={{ ...mockProfile, bio: "a\nb\nc\nd\ne\nf" }}
        isOwner={false}
        onEditClick={vi.fn()}
      />,
    );
    const toggle = screen.getByRole("button", { name: "More" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle.previousElementSibling?.className).toContain("line-clamp-3");
  });

  it("breaks long unbroken bio text and long names instead of overflowing", () => {
    render(
      <ProfileHeader
        profile={{ ...mockProfile, bio: "h".repeat(300) }}
        isOwner={false}
        onEditClick={vi.fn()}
      />,
    );
    expect(screen.getByText("h".repeat(300)).className).toContain("wrap-break-word");
    expect(screen.getByRole("heading", { name: "Elminster" }).className).toContain(
      "wrap-break-word",
    );
  });

  it("does not offer More for a short bio", () => {
    render(
      <ProfileHeader
        profile={mockProfile}
        isOwner={false}
        onEditClick={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "More" })).toBeNull();
  });

  it("renders CampaignCard with active status and handles abandon confirmation", () => {
    const mockCampaign: UserPlaythroughSummary = {
      playthrough_id: "pt-1",
      scenario_id: "sc-1",
      scenario_title: "Curse of Strahd",
      scenario_mode: "master",
      cover_image_url: null,
      turn_count: 22,
      status: "active",
      ended_outcome_tag: null,
      ended_outcome_title: null,
      ended_outcome_text: null,
      character_name: "Drizzt",
      character_archetype: "Ranger",
      created_at: "2026-10-27T00:00:00Z",
      updated_at: "2026-10-27T00:00:00Z",
    };

    const handleAbandon = vi.fn();

    render(
      <MemoryRouter>
        <CampaignCard campaign={mockCampaign} onAbandon={handleAbandon} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Curse of Strahd")).toBeInTheDocument();
    expect(screen.getByText("In progress")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute(
      "href",
      "/play/pt-1",
    );
    expect(screen.getByText(/Turn 22/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Abandon" }));
    expect(screen.getByText("Abandon run?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    expect(handleAbandon).toHaveBeenCalledWith("pt-1");
  });

  it("renders a completed CampaignCard with outcome, recap link and no Abandon", () => {
    const completed: UserPlaythroughSummary = {
      playthrough_id: "pt-2",
      scenario_id: "sc-1",
      scenario_title: "Curse of Strahd",
      scenario_mode: "master",
      cover_image_url: null,
      turn_count: 40,
      status: "completed",
      ended_outcome_tag: "win",
      ended_outcome_title: "The Long Road Home",
      ended_outcome_text: null,
      character_name: null,
      character_archetype: null,
      created_at: "2026-10-27T00:00:00Z",
      updated_at: "2026-10-27T00:00:00Z",
    };
    render(
      <MemoryRouter>
        <CampaignCard campaign={completed} onAbandon={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Victory")).toBeInTheDocument();
    expect(screen.getByText("The Long Road Home")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View recap" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abandon" })).toBeNull();
  });

  it("renders an abandoned CampaignCard with a recap link", () => {
    const abandoned = {
      playthrough_id: "pt-3",
      scenario_id: "sc-1",
      scenario_title: "Curse of Strahd",
      scenario_mode: "newbie",
      cover_image_url: null,
      turn_count: 3,
      status: "abandoned",
      ended_outcome_tag: null,
      ended_outcome_title: null,
      ended_outcome_text: null,
      character_name: null,
      character_archetype: null,
      created_at: "2026-10-27T00:00:00Z",
      updated_at: "2026-10-27T00:00:00Z",
    } as UserPlaythroughSummary;
    render(
      <MemoryRouter>
        <CampaignCard campaign={abandoned} onAbandon={vi.fn()} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Abandoned")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View recap" })).toBeInTheDocument();
  });

  const mockReview: UserReviewSummary = {
    review_id: "rev-1",
    scenario_id: "sc-2",
    scenario_title: "Tomb of Horrors",
    rating: 4,
    review_text: "A treacherous dungeon with ingenious traps!",
    created_at: "2026-10-27T00:00:00Z",
  };

  it("renders UserReviewCard with title link, comment, and an accessible rating", () => {
    render(
      <MemoryRouter>
        <UserReviewCard review={mockReview} />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("link", { name: "Tomb of Horrors" }),
    ).toHaveAttribute("href", "/scenario/sc-2");
    expect(screen.getByText(/ingenious traps/)).toBeInTheDocument();
    expect(screen.getByText("Rated 4 out of 5")).toBeInTheDocument();
  });

  it("shows a fallback when a review has no text", () => {
    render(
      <MemoryRouter>
        <UserReviewCard review={{ ...mockReview, review_text: null }} />
      </MemoryRouter>,
    );
    expect(screen.getByText("No written review.")).toBeInTheDocument();
  });
});
