import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScenarioMiniCard } from "../components/cards/ScenarioMiniCard";
import type { ScenarioSummaryResponse } from "@/features/play/types/scenario";

const scenario = {
  scenario_id: "sc-1",
  title: "The Grey Ledger",
  logline: "A detective tracks a missing ledger.",
  cover_image_url: null,
  genre_tags: ["Noir / Detective"],
  mode: "master",
  rating_avg: "4.25",
  play_count: 12,
} as unknown as ScenarioSummaryResponse;

describe("ScenarioMiniCard", () => {
  it("renders title, logline, genre, rating and plays", () => {
    render(<ScenarioMiniCard scenario={scenario} />);
    expect(screen.getByText("The Grey Ledger")).toBeInTheDocument();
    expect(screen.getByText(/missing ledger/)).toBeInTheDocument();
    expect(screen.getByText("Noir / Detective")).toBeInTheDocument();
    expect(screen.getByText("4.3")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("falls back when there is no cover, genre or logline", () => {
    const bare = {
      ...scenario,
      cover_image_url: null,
      genre_tags: [],
      logline: null,
    } as unknown as ScenarioSummaryResponse;
    render(<ScenarioMiniCard scenario={bare} />);
    expect(
      screen.getByRole("img", { name: "The Grey Ledger" }),
    ).toHaveAttribute("src", "/images/hero.png");
  });

  it("renders provided actions", () => {
    render(
      <ScenarioMiniCard
        scenario={scenario}
        overlayAction={<button>Remove</button>}
        footerAction={<button>Play</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
  });
});
