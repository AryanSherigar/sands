import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReaderVignette } from "./ReaderVignette";

describe("ReaderVignette", () => {
  it("is hidden from assistive technology and ignores the pointer", () => {
    const { container } = render(
      <ReaderVignette strength={0.3} theme="dark-velvet" shouldAnimate />,
    );

    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg?.getAttribute("class")).toContain("pointer-events-none");
    expect(svg).not.toHaveAttribute("style");
  });

  it("carries the strength as the fill opacity", () => {
    const { container } = render(
      <ReaderVignette strength={0.4} theme="dark-velvet" shouldAnimate />,
    );

    expect(container.querySelector("rect")).toHaveAttribute("fill-opacity", "0.4");
  });

  it("exposes the theme so the colour can follow it", () => {
    const { container } = render(
      <ReaderVignette strength={0.2} theme="antique-sepia" shouldAnimate />,
    );

    expect(container.querySelector("svg")).toHaveAttribute("data-theme", "antique-sepia");
  });

  it("only animates the strength change when allowed", () => {
    const { container, rerender } = render(
      <ReaderVignette strength={0.2} theme="dark-velvet" shouldAnimate />,
    );
    expect(container.querySelector(".vignette-fill-animated")).not.toBeNull();

    rerender(<ReaderVignette strength={0.2} theme="dark-velvet" shouldAnimate={false} />);
    expect(container.querySelector(".vignette-fill-animated")).toBeNull();
  });
});
