import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";
import { usePlayStore } from "../../stores/play.store";
import { PlaythroughData } from "../../types/play.types";
import { RulesClipboardContainer } from "./RulesClipboardContainer";

vi.mock("@/shared/lib/font-loader", () => ({ loadNarrationFont: vi.fn() }));

const sheet: RuleSheetItem[] = [
  {
    key: "r1",
    number: 1,
    text: "Never leave the desk before dawn.",
    status: "intact",
    source_style: "typed",
  },
];

const setPlaythrough = (overrides: Partial<PlaythroughData> = {}): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      enabled_tools: ["rule_sheet"],
      rule_sheet: sheet,
      ...overrides,
    } as PlaythroughData,
  });
};

describe("RulesClipboardContainer", () => {
  beforeEach(() => {
    usePlayStore.setState({ playthrough: null });
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
  });

  it("shows the revealed rules when the tool is on", () => {
    setPlaythrough();

    render(<RulesClipboardContainer />);

    expect(
      screen.getByText("Never leave the desk before dawn."),
    ).toBeInTheDocument();
  });

  it("renders nothing for a scenario without the tool, even if rules exist", () => {
    setPlaythrough({ enabled_tools: [] });

    const { container } = render(<RulesClipboardContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing until a rule has been revealed", () => {
    setPlaythrough({ rule_sheet: [] });

    const { container } = render(<RulesClipboardContainer />);

    expect(container).toBeEmptyDOMElement();
  });

  it("follows the store when a rule is revealed and another is violated", () => {
    setPlaythrough();
    render(<RulesClipboardContainer />);

    act(() => {
      setPlaythrough({
        rule_sheet: [
          { ...sheet[0], status: "violated" },
          {
            key: "r2",
            number: 2,
            text: "Never open the Records Cage.",
            status: "intact",
            source_style: "ink",
          },
        ],
      });
    });

    expect(screen.getByText("Never open the Records Cage.")).toBeInTheDocument();
    expect(screen.getByText("Rules broken: 1")).toBeInTheDocument();
  });

  it("uses reduced motion when the reader asks to reduce effects", () => {
    useReaderPreferencesStore.setState({ reduceSensoryEffects: true });
    setPlaythrough();

    render(<RulesClipboardContainer />);

    expect(
      screen.getByRole("complementary", { name: "Rules clipboard" }),
    ).toHaveAttribute("data-motion", "reduced");
  });

  it("offers a toggle that opens and closes the narrow-screen drawer", async () => {
    setPlaythrough();
    render(<RulesClipboardContainer />);
    const toggle = screen.getByRole("button", { name: /Rules \(1\)/ });

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.setup().click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.setup().click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
