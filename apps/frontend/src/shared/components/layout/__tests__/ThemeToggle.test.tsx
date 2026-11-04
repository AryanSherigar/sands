import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "../ThemeToggle";
import { useAppThemeStore } from "@/shared/stores/appTheme.store";

describe("ThemeToggle", () => {
  beforeEach(() => {
    useAppThemeStore.setState({ theme: "light" });
  });

  it("renders with dark mode switch label when in light theme", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: /switch to dark theme/i })).toBeInTheDocument();
  });

  it("toggles theme on click and updates aria label", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    const button = screen.getByRole("button", { name: /switch to dark theme/i });
    await user.click(button);
    expect(useAppThemeStore.getState().theme).toBe("dark");
    expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeInTheDocument();
  });
});
