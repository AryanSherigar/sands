import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Button } from "../Button";

describe("Button Primitive (Quiet Cinematic)", () => {
  it("renders primary button with solid off-white background and 10px radius", () => {
    render(<Button variant="primary">Start Game</Button>);
    const button = screen.getByRole("button", { name: /start game/i });
    expect(button.className).toContain("bg-primary");
    expect(button.className).toContain("text-primary-contrast");
    expect(button.className).toContain("rounded-md");
  });

  it("renders secondary button with surface-raised and border-strong", () => {
    render(<Button variant="secondary">Cancel</Button>);
    const button = screen.getByRole("button", { name: /cancel/i });
    expect(button.className).toContain("bg-surface-raised");
    expect(button.className).toContain("border-border-strong");
    expect(button.className).toContain("text-content");
  });

  it("applies standardized height for md size", () => {
    render(<Button size="md">Action</Button>);
    const button = screen.getByRole("button", { name: /action/i });
    expect(button.className).toContain("h-10");
  });

  it("defaults to primary variant and md size", () => {
    render(<Button>Default</Button>);
    const button = screen.getByRole("button", { name: /default/i });
    expect(button.className).toContain("bg-primary");
    expect(button.className).toContain("h-10");
  });

  it("renders ghost variant with text-content-muted and hover:bg-white/6", () => {
    render(<Button variant="ghost">Ghost Action</Button>);
    const button = screen.getByRole("button", { name: /ghost action/i });
    expect(button.className).toContain("bg-transparent");
    expect(button.className).toContain("text-content-muted");
    expect(button.className).toContain("hover:bg-white/6");
  });

  it("renders danger variant with border-danger/30", () => {
    render(<Button variant="danger">Delete</Button>);
    const button = screen.getByRole("button", { name: /delete/i });
    expect(button.className).toContain("text-danger");
    expect(button.className).toContain("border-danger/30");
  });

  it("renders accent variant with border-accent and text-accent", () => {
    render(<Button variant="accent">Explore</Button>);
    const button = screen.getByRole("button", { name: /explore/i });
    expect(button.className).toContain("text-accent");
    expect(button.className).toContain("border-accent");
  });

  it("applies standardized height for sm and lg sizes", () => {
    const { rerender } = render(<Button size="sm">Small</Button>);
    const smallBtn = screen.getByRole("button", { name: /small/i });
    expect(smallBtn.className).toContain("h-8");
    expect(smallBtn.className).toContain("px-3");

    rerender(<Button size="lg">Large</Button>);
    const largeBtn = screen.getByRole("button", { name: /large/i });
    expect(largeBtn.className).toContain("h-12");
    expect(largeBtn.className).toContain("px-6");
  });

  it("applies disabled styles and disabled attribute", () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByRole("button", { name: /disabled/i });
    expect(button).toBeDisabled();
    expect(button.className).toContain("disabled:opacity-40");
    expect(button.className).toContain("disabled:cursor-not-allowed");
  });

  it("applies focus ring with ring-primary and offset-surface", () => {
    render(<Button>Focus</Button>);
    const button = screen.getByRole("button", { name: /focus/i });
    expect(button.className).toContain("focus-visible:ring-primary");
    expect(button.className).toContain("focus-visible:ring-offset-surface");
  });

  it("forwards ref to the underlying button element", () => {
    const ref = React.createRef<HTMLButtonElement>();
    render(<Button ref={ref}>With Ref</Button>);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});
