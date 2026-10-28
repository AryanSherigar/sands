import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { UserDropdown } from "../UserDropdown";

describe("UserDropdown", () => {
  it("links to creator stats", async () => {
    render(
      <MemoryRouter>
        <UserDropdown
          user={{ user_id: "u1", display_name: "Eldrin", onboarding_completed: true }}
          onLogout={vi.fn()}
        />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("button", { name: /Eldrin/ }));

    expect(screen.getByRole("link", { name: "Creator stats" })).toHaveAttribute(
      "href",
      "/studio/stats",
    );
  });
});
