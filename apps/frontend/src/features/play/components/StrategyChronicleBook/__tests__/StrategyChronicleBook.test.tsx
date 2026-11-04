import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StrategyChronicleBook } from "../StrategyChronicleBook";

const startEpilogue = vi.fn();
let book = {
  chapters: [] as { summaryId: string; turn: number; narration: string }[],
  isPreparing: false,
};
let epilogue = {
  narration: "",
  status: "pending" as "pending" | "streaming" | "completed" | "failed",
  errorMessage: null as string | null,
  start: startEpilogue,
};

vi.mock("../../../hooks/useStrategyChronicleBook", () => ({
  useStrategyChronicleBook: () => book,
}));
vi.mock("../../../hooks/useStrategyEpilogue", () => ({
  useStrategyEpilogue: () => epilogue,
}));

function renderBook(onClose = vi.fn()) {
  render(
    <StrategyChronicleBook
      playthroughId="pt-1"
      rulerName="King Alden IV"
      chroniclerId="vaelen"
      eraLabel="Spring 1042 to Winter 1051"
      onClose={onClose}
    />,
  );
  return onClose;
}

describe("StrategyChronicleBook", () => {
  beforeEach(() => {
    startEpilogue.mockReset();
    book = { chapters: [], isPreparing: false };
    epilogue = { narration: "", status: "pending", errorMessage: null, start: startEpilogue };
  });

  it("opens on a cover with the ruler and the chronicler's name", () => {
    renderBook();
    expect(screen.getByRole("heading", { name: "King Alden IV" })).toBeInTheDocument();
    expect(screen.getByText(/Vaelen the Scorned/)).toBeInTheDocument();
    expect(screen.getByText("Spring 1042 to Winter 1051")).toBeInTheDocument();
  });

  it("shows chapters in order and then the closing entry", () => {
    book = {
      chapters: [
        { summaryId: "a", turn: 3, narration: "The first winter was hard." },
        { summaryId: "b", turn: 9, narration: "The marches rose in spring." },
      ],
      isPreparing: false,
    };
    epilogue = { ...epilogue, status: "completed", narration: "They remember a cruel crown." };
    renderBook();
    const text = screen.getByRole("article").textContent ?? "";
    expect(text.indexOf("The first winter was hard.")).toBeLessThan(
      text.indexOf("The marches rose in spring."),
    );
    expect(text.indexOf("The marches rose in spring.")).toBeLessThan(
      text.indexOf("They remember a cruel crown."),
    );
  });

  it("shows only the cover and the closing entry when no chronicles exist", () => {
    epilogue = { ...epilogue, status: "completed", narration: "Few remember the short reign." };
    renderBook();
    expect(screen.queryByTestId("book-chapter")).toBeNull();
    expect(screen.getByText("Few remember the short reign.")).toBeInTheDocument();
  });

  it("says the record is being finished while entries are written and holds the closing entry", () => {
    book = { chapters: [], isPreparing: true };
    renderBook();
    expect(screen.getByText("The chronicler is finishing the record…")).toBeInTheDocument();
    expect(startEpilogue).not.toHaveBeenCalled();
  });

  it("starts the closing entry once the book is ready and it is not saved", () => {
    renderBook();
    expect(startEpilogue).toHaveBeenCalledTimes(1);
  });

  it("does not start the closing entry again when it is already saved", () => {
    epilogue = { ...epilogue, status: "completed", narration: "Saved." };
    renderBook();
    expect(startEpilogue).not.toHaveBeenCalled();
  });

  it("offers a retry when the closing entry failed", () => {
    epilogue = { ...epilogue, status: "failed", errorMessage: "Try again." };
    renderBook();
    startEpilogue.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(startEpilogue).toHaveBeenCalledTimes(1);
  });

  it("shows no outcome tier and no score anywhere in the book", () => {
    book = { chapters: [{ summaryId: "a", turn: 3, narration: "Winter came." }], isPreparing: false };
    epilogue = { ...epilogue, status: "completed", narration: "A quiet end." };
    renderBook();
    const text = screen.getByRole("article").textContent ?? "";
    expect(text).not.toMatch(/triumph|ruin|bitter|honorable|pyrrhic|score|grade/i);
  });

  it("closes back to the ending screen", () => {
    const onClose = renderBook();
    fireEvent.click(screen.getByRole("button", { name: "Close the book" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("offers to copy or save the whole book once the closing entry is written", () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    book = { chapters: [{ summaryId: "a", turn: 3, narration: "The first winter was hard." }], isPreparing: false };
    epilogue = { ...epilogue, status: "completed", narration: "They remember a cruel crown." };
    renderBook();

    fireEvent.click(screen.getByRole("button", { name: "Copy the book" }));

    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText.mock.calls[0][0]).toContain("The first winter was hard.");
    expect(writeText.mock.calls[0][0]).toContain("They remember a cruel crown.");
    expect(screen.getByRole("button", { name: "Save as a text file" })).toBeInTheDocument();
  });

  it("hides sharing until the book is finished", () => {
    book = { chapters: [], isPreparing: true };
    renderBook();
    expect(screen.queryByRole("button", { name: "Copy the book" })).toBeNull();
  });
});
