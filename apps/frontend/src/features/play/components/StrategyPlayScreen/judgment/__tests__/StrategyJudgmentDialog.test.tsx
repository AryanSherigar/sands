import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { StrategyJudgmentPackage } from "../../../../types/judgmentScene.types";
import { StrategyJudgmentDialog } from "../StrategyJudgmentDialog";
import type { StrategyJudgmentDialogProps } from "../StrategyJudgmentDialog.types";

const OPENING = 'The hall is silent.\nBRANNOCH: "An open defiance requires an open reckoning."';

const basePackage = (overrides: Partial<StrategyJudgmentPackage> = {}): StrategyJudgmentPackage => ({
  sceneId: "scene-j",
  turn: 5,
  summary: "Harl, governor of Ash Ford, stands accused before Valdren.",
  charge: "an uprising in their region has been crushed",
  subjectKind: "governor",
  accused: { participantId: "harl", name: "Harl", kind: "governor", stance: null },
  advisors: [
    { participantId: "veyra", name: "Veyra", kind: "governor", stance: "mercy" },
    { participantId: "brannoch", name: "Brannoch", kind: "officer", stance: "iron" },
  ],
  openingText: OPENING,
  exchanges: [],
  spokenExchangesRemaining: 4,
  outcomeSummary: [],
  isResolved: false,
  ...overrides,
});

const setup = (
  pkgOverrides: Partial<StrategyJudgmentPackage> = {},
  props: Partial<StrategyJudgmentDialogProps> = {},
) => {
  const handlers = {
    onSpeak: vi.fn(() => Promise.resolve(true)),
    onPronounce: vi.fn(() => Promise.resolve(true)),
    onDismissReveal: vi.fn(),
    onClose: vi.fn(),
  };
  const user = userEvent.setup();
  render(
    <StrategyJudgmentDialog
      isOpen
      pkg={basePackage(pkgOverrides)}
      liveText=""
      isStreaming={false}
      failureMessage={null}
      {...handlers}
      {...props}
    />,
  );
  return { user, ...handlers };
};

const verdictButton = (name: RegExp) =>
  within(screen.getByRole("group", { name: /verdict/i })).getByRole("button", { name });

describe("StrategyJudgmentDialog", () => {
  it("renders nothing when closed", () => {
    render(
      <StrategyJudgmentDialog
        isOpen={false}
        pkg={basePackage()}
        liveText=""
        isStreaming={false}
        failureMessage={null}
        onSpeak={vi.fn()}
        onPronounce={vi.fn()}
        onDismissReveal={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows the accused and each advisor with a text label for their stance", () => {
    setup();
    expect(screen.getByRole("dialog", { name: /judgment of harl/i })).toBeInTheDocument();
    const court = within(screen.getByRole("region", { name: /the court/i }));
    expect(court.getByText("Harl")).toBeInTheDocument();
    expect(court.getByText("Veyra")).toBeInTheDocument();
    expect(court.getByText("Urges mercy")).toBeInTheDocument();
    expect(court.getByText("Brannoch")).toBeInTheDocument();
    expect(court.getByText("Iron example")).toBeInTheDocument();
    expect(screen.getByText(/uprising in their region has been crushed/i)).toBeInTheDocument();
  });

  it("renders only the court cards that are present", () => {
    setup({ advisors: [{ participantId: "veyra", name: "Veyra", kind: "governor", stance: "mercy" }] });
    const court = within(screen.getByRole("region", { name: /the court/i }));
    expect(court.getByText("Urges mercy")).toBeInTheDocument();
    expect(court.queryByText("Iron example")).toBeNull();
  });

  it("renders the tableau as narration and speaker-tagged speech", () => {
    setup();
    expect(screen.getByText("The hall is silent.")).toBeInTheDocument();
    expect(screen.getByText(/An open defiance requires an open reckoning/)).toBeInTheDocument();
    expect(screen.getAllByText("Brannoch").length).toBeGreaterThan(0);
  });

  it("shows a convening note before the tableau has arrived", () => {
    setup({ openingText: "" });
    expect(screen.getByText(/the court is being convened/i)).toBeInTheDocument();
  });

  it("offers the four verdicts with a label and tagline but no effects", () => {
    setup();
    const group = screen.getByRole("group", { name: /verdict/i });
    for (const label of ["Release", "Exile", "Imprison", "Execute"]) {
      expect(within(group).getByText(label)).toBeInTheDocument();
    }
    expect(within(group).getByText("The headsman's axe")).toBeInTheDocument();
    expect(group.textContent).not.toMatch(/[+\-−]\s?\d/);
  });

  it("starts with imprison selected", () => {
    setup();
    expect(verdictButton(/imprison/i)).toHaveAttribute("aria-pressed", "true");
    expect(verdictButton(/execute/i)).toHaveAttribute("aria-pressed", "false");
  });

  it("selects verdicts with keys 1 to 4 and swaps the nuance chips", async () => {
    const { user } = setup();
    await user.keyboard("4");
    expect(verdictButton(/execute/i)).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "publicly" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "for life" })).toBeNull();
    await user.keyboard("1");
    expect(screen.getByRole("button", { name: "with a pardon" })).toBeInTheDocument();
  });

  it("does not change the verdict when a digit is typed into the input", async () => {
    const { user } = setup();
    await user.type(screen.getByRole("textbox"), "4");
    expect(verdictButton(/imprison/i)).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("textbox")).toHaveValue("4");
  });

  it("pronounces the default imprisonment with no nuance and no decree text", async () => {
    const { user, onPronounce } = setup();
    await user.click(screen.getByRole("button", { name: /pronounce judgment/i }));
    expect(onPronounce).toHaveBeenCalledWith({
      verdict: "imprison",
      nuance: null,
      decreeText: "",
    });
  });

  it("pronounces the chosen verdict, nuance and decree wording", async () => {
    const { user, onPronounce } = setup();
    await user.keyboard("4");
    await user.click(screen.getByRole("button", { name: "publicly" }));
    await user.type(screen.getByRole("textbox"), "Let it be seen.");
    await user.click(screen.getByRole("button", { name: /pronounce judgment/i }));
    expect(onPronounce).toHaveBeenCalledWith({
      verdict: "execute",
      nuance: "publicly",
      decreeText: "Let it be seen.",
    });
  });

  it("clears the nuance when the verdict changes", async () => {
    const { user, onPronounce } = setup();
    await user.keyboard("4");
    await user.click(screen.getByRole("button", { name: "publicly" }));
    await user.keyboard("1");
    await user.click(screen.getByRole("button", { name: /pronounce judgment/i }));
    expect(onPronounce).toHaveBeenCalledWith({
      verdict: "release",
      nuance: null,
      decreeText: "",
    });
  });

  it("speaks to the court and clears the input", async () => {
    const { user, onSpeak } = setup();
    await user.type(screen.getByRole("textbox"), "Why did you rise?");
    await user.click(screen.getByRole("button", { name: /^speak/i }));
    expect(onSpeak).toHaveBeenCalledWith("Why did you rise?");
    expect(screen.getByRole("textbox")).toHaveValue("");
  });

  it("speaks when Enter is pressed in the input rather than pronouncing", async () => {
    const { user, onSpeak, onPronounce } = setup();
    await user.type(screen.getByRole("textbox"), "Speak plainly{Enter}");
    expect(onSpeak).toHaveBeenCalledWith("Speak plainly");
    expect(onPronounce).not.toHaveBeenCalled();
  });

  it("fills the input from a whisper", async () => {
    const { user } = setup();
    const whisper = screen.getAllByRole("button", { name: /kneel before this court/i })[0];
    await user.click(whisper);
    expect(screen.getByRole("textbox")).toHaveValue(whisper.textContent ?? "");
  });

  it("stops accepting speech once only the pronouncement remains", () => {
    setup({ spokenExchangesRemaining: 0 });
    expect(screen.getByRole("button", { name: /^speak/i })).toBeDisabled();
    expect(screen.getByText(/the court has heard enough/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pronounce judgment/i })).toBeEnabled();
  });

  it("disables the controls and shows the live reply while the court is speaking", () => {
    setup({}, { isStreaming: true, liveText: 'HARL: "I did what any man would do."' });
    expect(screen.getByRole("button", { name: /pronounce judgment/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /^speak/i })).toBeDisabled();
    expect(screen.getByText(/I did what any man would do/)).toBeInTheDocument();
  });

  it("announces a failure", () => {
    setup({}, { failureMessage: "The court could not be heard. Try again." });
    expect(screen.getByRole("alert")).toHaveTextContent("The court could not be heard");
  });

  it("asks before leaving, because leaving imprisons the accused", async () => {
    const { user, onClose } = setup();
    await user.click(screen.getByRole("button", { name: /exit/i }));
    expect(screen.getByText(/leaving the hall imprisons the accused/i)).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /stay/i }));
    expect(screen.queryByText(/leaving the hall imprisons/i)).toBeNull();
    await user.click(screen.getByRole("button", { name: /exit/i }));
    await user.click(screen.getByRole("button", { name: /leave the hall/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("treats Escape as a request to leave, never as leaving", async () => {
    const { user, onClose } = setup();
    await user.keyboard("{Escape}");
    expect(screen.getByText(/leaving the hall imprisons the accused/i)).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("reveals the consequences with their causes once the scene has resolved", async () => {
    const { user, onDismissReveal } = setup({
      isResolved: true,
      outcomeSummary: [
        "Judgment: Executed (publicly).",
        "Regard of the accused's house: -26 (cruelty shown).",
      ],
    });
    expect(screen.getByText("Judgment: Executed (publicly).")).toBeInTheDocument();
    expect(screen.getByText(/-26 \(cruelty shown\)/)).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: /verdict/i })).toBeNull();
    await user.click(screen.getByRole("button", { name: /return to the realm/i }));
    expect(onDismissReveal).toHaveBeenCalledTimes(1);
  });

  it("animates the seal only for people who have not asked for reduced motion", () => {
    setup({ isResolved: true, outcomeSummary: ["Judgment: Released."] });
    const seal = screen.getByTestId("judgment-seal");
    expect(seal.className).toContain("motion-safe:");
    expect(seal.className).not.toMatch(/(^|\s)animate-/);
  });

  it("offers a retry when the court failed to open", async () => {
    const onRetryOpen = vi.fn();
    const { user } = setup({}, { failureMessage: "The court could not convene.", canRetryOpen: true, onRetryOpen });

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(onRetryOpen).toHaveBeenCalledTimes(1);
  });
});
