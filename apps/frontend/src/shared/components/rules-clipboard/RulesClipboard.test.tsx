import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";
import { RulesClipboard } from "./RulesClipboard";

const rule = (
  number: number,
  overrides: Partial<RuleSheetItem> = {},
): RuleSheetItem => ({
  key: `r${number}`,
  number,
  text: `Rule ${number} wording`,
  status: "intact",
  source_style: "typed",
  ...overrides,
});

describe("RulesClipboard", () => {
  it("lists duties above the rules", () => {
    render(
      <RulesClipboard
        rules={[rule(1)]}
        duties={["Sign in visitors", "File folders"]}
        isMotionReduced
      />,
    );
    const duties = screen.getByRole("list", { name: "Duties" });
    expect(
      within(duties)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Sign in visitors", "File folders"]);
  });

  it("shows no duties section without duties", () => {
    render(<RulesClipboard rules={[rule(1)]} isMotionReduced />);
    expect(screen.queryByRole("list", { name: "Duties" })).toBeNull();
  });

  it("renders the block-ink hand class", () => {
    render(
      <RulesClipboard
        rules={[rule(6, { source_style: "ink_block" })]}
        isMotionReduced
      />,
    );
    expect(document.querySelector(".rule-hand-ink_block")).not.toBeNull();
  });

  it("is a labelled region holding an ordered list of rules", () => {
    render(
      <RulesClipboard rules={[rule(1), rule(2)]} isMotionReduced={false} />,
    );

    const region = screen.getByRole("complementary", { name: "Rules clipboard" });
    const items = within(within(region).getByRole("list")).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Rule 1 wording");
  });

  it.each([
    ["intact", "intact"],
    ["active_threat", "under threat"],
    ["violated", "violated"],
    ["corrupted", "corrupted"],
  ] as const)("shows the %s status as text, not only as styling", (status, label) => {
    render(
      <RulesClipboard rules={[rule(3, { status })]} isMotionReduced={false} />,
    );

    expect(screen.getByText(new RegExp(`Rule 3, ${label}`))).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveAttribute("data-status", status);
  });

  it("adds a tally mark to the footer for each violated rule", () => {
    render(
      <RulesClipboard
        rules={[
          rule(1, { status: "violated" }),
          rule(2, { status: "violated" }),
          rule(3),
        ]}
        isMotionReduced={false}
      />,
    );

    expect(screen.getByText("Rules broken: 2")).toBeInTheDocument();
  });

  it("shows no tally while nothing is violated", () => {
    render(<RulesClipboard rules={[rule(1)]} isMotionReduced={false} />);

    expect(screen.queryByText(/Rules broken/)).toBeNull();
  });

  it("renders a corrupted rule's text as it was given (the server swaps it)", () => {
    render(
      <RulesClipboard
        rules={[rule(4, { status: "corrupted", text: "Never answer... the phone" })]}
        isMotionReduced={false}
      />,
    );

    expect(screen.getByText("Never answer... the phone")).toBeInTheDocument();
  });

  it("applies the handwriting hand of each rule", () => {
    render(
      <RulesClipboard
        rules={[rule(1, { source_style: "pencil" })]}
        isMotionReduced={false}
      />,
    );

    expect(screen.getByRole("listitem")).toHaveClass("rule-hand-pencil");
  });

  it("announces newly added rules politely", () => {
    render(<RulesClipboard rules={[rule(1)]} isMotionReduced={false} />);

    const list = screen.getByRole("list");
    expect(list).toHaveAttribute("aria-live", "polite");
    expect(list).toHaveAttribute("aria-relevant", "additions");
  });

  it("marks the panel reduced-motion so the pulse and glitch stop", () => {
    render(<RulesClipboard rules={[rule(1)]} isMotionReduced />);

    expect(
      screen.getByRole("complementary", { name: "Rules clipboard" }),
    ).toHaveAttribute("data-motion", "reduced");
  });
});
