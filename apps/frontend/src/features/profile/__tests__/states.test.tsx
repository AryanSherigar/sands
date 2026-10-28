import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { TabEmptyState } from "../components/states/TabEmptyState";
import { TabErrorState } from "../components/states/TabErrorState";
import { TabSkeleton } from "../components/states/TabSkeleton";

describe("tab states", () => {
  it("empty state shows the message and one action link", () => {
    render(
      <MemoryRouter>
        <TabEmptyState
          message="No runs yet"
          action={{ label: "Explore stories", to: "/discover" }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("No runs yet")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Explore stories" }),
    ).toHaveAttribute("href", "/discover");
  });

  it("empty state without an action renders no link", () => {
    render(
      <MemoryRouter>
        <TabEmptyState message="No reviews yet" />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("error state is announced and pairs an icon with text", () => {
    render(<TabErrorState message="Couldn't load campaigns" />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Couldn't load campaigns");
    expect(alert.querySelector("svg")).not.toBeNull();
  });

  it("skeleton is a busy status region", () => {
    render(<TabSkeleton />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });
});
