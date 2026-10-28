import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ViewingAsBar } from "../components/ViewingAsBar/ViewingAsBar";
import { useProfilePreviewStore } from "../stores/profilePreview.store";

describe("ViewingAsBar", () => {
  beforeEach(() => {
    useProfilePreviewStore.setState({ isPreviewingAsVisitor: false });
  });

  it("defaults to Owner and switches to Public Visitor", () => {
    render(<ViewingAsBar />);
    expect(screen.getByRole("radio", { name: "Owner (You)" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.click(screen.getByRole("radio", { name: "Public Visitor" }));
    expect(useProfilePreviewStore.getState().isPreviewingAsVisitor).toBe(true);
  });

  it("is hidden below the md breakpoint via classes", () => {
    const { container } = render(<ViewingAsBar />);
    expect(container.firstElementChild?.className).toContain("hidden");
    expect(container.firstElementChild?.className).toContain("md:flex");
  });
});
