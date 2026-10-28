import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileTabs } from "../components/ProfileTabs/ProfileTabs";
import { getVisibleTabs } from "../lib/profileTabs";

describe("ProfileTabs", () => {
  it("renders a tablist with the active tab selected", () => {
    render(
      <ProfileTabs
        tabs={getVisibleTabs(true)}
        activeTab="campaigns"
        onTabChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("tablist")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Campaigns" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: "Creations" })).toHaveAttribute(
      "tabindex",
      "-1",
    );
  });

  it("does not render tabs it was not given", () => {
    render(
      <ProfileTabs
        tabs={getVisibleTabs(false)}
        activeTab="creations"
        onTabChange={vi.fn()}
      />,
    );
    expect(screen.queryByRole("tab", { name: "Campaigns" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Bookmarks" })).toBeNull();
  });

  it("selects on click and moves with arrow keys", () => {
    const handleChange = vi.fn();
    render(
      <ProfileTabs
        tabs={getVisibleTabs(true)}
        activeTab="creations"
        onTabChange={handleChange}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: "Reviews" }));
    expect(handleChange).toHaveBeenLastCalledWith("reviews");

    fireEvent.keyDown(screen.getByRole("tab", { name: "Creations" }), {
      key: "ArrowRight",
    });
    expect(handleChange).toHaveBeenLastCalledWith("campaigns");
  });
});
