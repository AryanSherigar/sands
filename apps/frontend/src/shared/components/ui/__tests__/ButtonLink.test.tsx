import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ButtonLink } from "../ButtonLink";

describe("ButtonLink", () => {
  it("renders an anchor to the target with button styling", () => {
    render(
      <MemoryRouter>
        <ButtonLink to="/discover" variant="secondary">
          Explore
        </ButtonLink>
      </MemoryRouter>,
    );
    const link = screen.getByRole("link", { name: "Explore" });
    expect(link).toHaveAttribute("href", "/discover");
    expect(link.className).toContain("bg-surface-raised");
  });
});
