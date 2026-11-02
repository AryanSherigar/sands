import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { StrategyArtFrame } from "../StrategyArtFrame";

describe("StrategyArtFrame", () => {
  it("shows a skeleton while loading", () => {
    render(<StrategyArtFrame artUrl={null} isLoading={true} altText="Grain riots" />);
    expect(screen.getByRole("status", { name: /painting the scene/i })).toBeInTheDocument();
  });

  it("renders the image with alt text", () => {
    render(
      <StrategyArtFrame artUrl="https://cdn.test/a.webp" isLoading={false} altText="Grain riots" />,
    );
    expect(screen.getByRole("img", { name: "Grain riots" })).toHaveAttribute(
      "src",
      "https://cdn.test/a.webp",
    );
  });

  it("renders nothing when there is no url and nothing is loading", () => {
    const { container } = render(
      <StrategyArtFrame artUrl={null} isLoading={false} altText="Grain riots" />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows a failure notice with a retry button instead of a permanent skeleton", () => {
    const handleRetry = vi.fn();
    render(
      <StrategyArtFrame artUrl={null} isLoading={false} altText="x" hasFailed onRetry={handleRetry} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByRole("alert")).toHaveTextContent("could not be painted");
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
