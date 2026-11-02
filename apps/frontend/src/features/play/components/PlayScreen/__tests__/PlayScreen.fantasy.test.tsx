import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { usePlayStore } from "../../../stores/play.store";
import type { PlaythroughData } from "../../../types/play.types";
import { PlayScreen } from "../PlayScreen";

vi.mock("../Fantasy/FantasyPlayScreen", () => ({ FantasyPlayScreen: () => <div>Fantasy reader</div> }));
vi.mock("../MasterPlayScreen", () => ({ MasterPlayScreen: () => <div>Advanced reader</div> }));
vi.mock("../NewbiePlayScreen", () => ({ NewbiePlayScreen: () => <div>Simple reader</div> }));
vi.mock("../StrategyPlayScreen", () => ({ StrategyPlayScreen: () => <div>Strategy reader</div> }));

describe("play screen selection", () => {
  beforeEach(() => usePlayStore.setState({ playthrough: null }));
  it.each(["master", "newbie"] as const)("uses fantasy for %s High Fantasy", (mode) => {
    usePlayStore.setState({ playthrough: { mode, genre_tags: ["High Fantasy"] } as PlaythroughData });
    render(<PlayScreen />);
    expect(screen.getByText("Fantasy reader")).toBeInTheDocument();
  });
  it("keeps Strategy independent of genre", () => {
    usePlayStore.setState({ playthrough: { mode: "strategy", genre_tags: ["High Fantasy"] } as PlaythroughData });
    render(<PlayScreen />);
    expect(screen.getByText("Strategy reader")).toBeInTheDocument();
  });
  it("uses legacy reader when tags are absent", () => {
    usePlayStore.setState({ playthrough: { mode: "master" } as PlaythroughData });
    render(<PlayScreen />);
    expect(screen.getByText("Advanced reader")).toBeInTheDocument();
  });
});
