import React, { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LoreBox } from "./LoreBox";
import type { LoreBoxProps } from "./LoreBox.types";
import type { LoreDocument } from "../../types/lore.types";
import type { QuestionGroup } from "../../types/guide.types";

const QUESTIONS: QuestionGroup[] = [
  {
    id: "voice-group",
    name: "Voice",
    questions: [
      { id: "voice", label: "Voice", prompt: "How do they talk?" },
      { id: "line", label: "A line", prompt: "Write one line they'd say." },
    ],
  },
  {
    id: "where-group",
    name: "Where",
    questions: [
      {
        id: "found-at",
        label: "Found at",
        prompt: "Where can the player usually find them?",
        pick: { kind: "place", predicate: "is usually found at" },
      },
    ],
  },
];

type HarnessProps = Partial<Omit<LoreBoxProps, "document" | "onChange">> & {
  initial?: LoreDocument;
  onDocument?: (next: LoreDocument) => void;
};

const Harness: React.FC<HarnessProps> = ({ initial, onDocument, ...rest }) => {
  const [document, setDocument] = useState<LoreDocument>(
    initial ?? { blocks: [] },
  );
  const handleChange = (next: LoreDocument): void => {
    setDocument(next);
    onDocument?.(next);
  };
  return <LoreBox document={document} onChange={handleChange} {...rest} />;
};

const openQuestion = async (
  user: ReturnType<typeof userEvent.setup>,
  groupName: string,
): Promise<void> => {
  await user.click(screen.getByRole("button", { name: /questions to help/i }));
  await user.click(screen.getByRole("button", { name: groupName }));
};

describe("LoreBox", () => {
  it("keeps Questions to Help folded until opened", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} />);

    expect(screen.queryByLabelText("How do they talk?")).not.toBeInTheDocument();
    await openQuestion(user, "Voice");

    expect(screen.getByLabelText("How do they talk?")).toBeInTheDocument();
  });

  it("shows how many questions are answered", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} />);
    expect(screen.getByText("0 of 3 answered")).toBeInTheDocument();

    await openQuestion(user, "Voice");
    await user.type(screen.getByLabelText("How do they talk?"), "Slow");

    expect(screen.getByText("1 of 3 answered")).toBeInTheDocument();
  });

  it("adds a labelled linked block when a question is answered", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} />);

    await openQuestion(user, "Voice");
    await user.type(screen.getByLabelText("How do they talk?"), "Slow and low");

    expect(screen.getByText("Voice ↔")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Voice" })).toHaveValue(
      "Slow and low",
    );
  });

  it("keeps the answer and the block body in sync both ways", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} />);
    await openQuestion(user, "Voice");
    const answer = screen.getByLabelText("How do they talk?");
    await user.type(answer, "Slow");

    await user.type(screen.getByRole("textbox", { name: "Voice" }), " and low");
    expect(answer).toHaveValue("Slow and low");

    await user.type(answer, "er");
    expect(screen.getByRole("textbox", { name: "Voice" })).toHaveValue(
      "Slow and lower",
    );
  });

  it("clears the answer when the block is deleted", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} />);
    await openQuestion(user, "Voice");
    await user.type(screen.getByLabelText("How do they talk?"), "Slow");

    await user.click(screen.getByRole("button", { name: "Voice options" }));
    await user.click(screen.getByRole("menuitem", { name: /delete/i }));

    expect(screen.queryByText("Voice ↔")).not.toBeInTheDocument();
    expect(screen.getByLabelText("How do they talk?")).toHaveValue("");
  });

  it("removes the block when the answer is cleared", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} />);
    await openQuestion(user, "Voice");
    const answer = screen.getByLabelText("How do they talk?");
    await user.type(answer, "Slow");

    await user.clear(answer);

    expect(screen.queryByText("Voice ↔")).not.toBeInTheDocument();
  });

  it("unlinks a block into plain text and empties the answer", async () => {
    const user = userEvent.setup();
    const onDocument = vi.fn();
    render(<Harness questions={QUESTIONS} onDocument={onDocument} />);
    await openQuestion(user, "Voice");
    await user.type(screen.getByLabelText("How do they talk?"), "Slow");

    await user.click(screen.getByRole("button", { name: "Voice options" }));
    await user.click(screen.getByRole("menuitem", { name: /unlink/i }));

    expect(screen.queryByText("Voice ↔")).not.toBeInTheDocument();
    expect(screen.getByLabelText("How do they talk?")).toHaveValue("");
    expect(screen.getByDisplayValue("Slow")).toBeInTheDocument();
    const lastDocument = onDocument.mock.calls.at(-1)?.[0] as LoreDocument;
    expect(lastDocument.blocks.every((block) => block.kind === "text")).toBe(true);
  });

  it("never links free writing to a question", async () => {
    const user = userEvent.setup();
    render(<Harness questions={QUESTIONS} ariaLabel="Premise" />);

    await user.type(screen.getByRole("textbox", { name: "Premise" }), "A storm.");
    await openQuestion(user, "Voice");

    expect(screen.getByLabelText("How do they talk?")).toHaveValue("");
    expect(screen.queryByText("Voice ↔")).not.toBeInTheDocument();
    expect(screen.getByText("0 of 3 answered")).toBeInTheDocument();
  });

  it("shows the soft word guide and a live word count", async () => {
    const user = userEvent.setup();
    render(<Harness softWordGuide="Aim for 50–150 words" ariaLabel="Premise" />);
    expect(screen.getByText("Aim for 50–150 words")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: "Premise" }), "one two three");

    expect(screen.getByText("3 words")).toBeInTheDocument();
  });

  it("offers Add to Always remember on a block and copies the line", async () => {
    const user = userEvent.setup();
    const onAddToAlwaysRemember = vi.fn();
    render(
      <Harness
        questions={QUESTIONS}
        onAddToAlwaysRemember={onAddToAlwaysRemember}
      />,
    );
    await openQuestion(user, "Voice");
    await user.type(screen.getByLabelText("How do they talk?"), "Slow");

    await user.click(screen.getByRole("button", { name: "Voice options" }));
    await user.click(
      screen.getByRole("menuitem", { name: /add to always remember/i }),
    );

    expect(onAddToAlwaysRemember).toHaveBeenCalledWith("Voice: Slow");
  });

  it("moves a block up and down from its menu", async () => {
    const user = userEvent.setup();
    const initial: LoreDocument = {
      blocks: [
        { kind: "answer", question_id: "voice", label: "Voice", text: "a" },
        { kind: "answer", question_id: "line", label: "A line", text: "b" },
      ],
    };
    const onDocument = vi.fn();
    render(<Harness initial={initial} onDocument={onDocument} />);

    await user.click(screen.getByRole("button", { name: "A line options" }));
    await user.click(screen.getByRole("menuitem", { name: /move up/i }));

    const next = onDocument.mock.calls.at(-1)?.[0] as LoreDocument;
    expect(next.blocks.map((block) => block.question_id)).toEqual(["line", "voice"]);
  });

  describe("pick questions", () => {
    const pickOptions = [
      { id: "place-1", name: "The Lighthouse", kind: "place" as const },
      { id: "char-1", name: "Mara", kind: "character" as const },
    ];

    it("lists only cards of the requested kind", async () => {
      const user = userEvent.setup();
      render(<Harness questions={QUESTIONS} pickOptions={pickOptions} />);
      await openQuestion(user, "Where");

      const picker = screen.getByLabelText("Where can the player usually find them?");

      expect(within(picker).getByRole("option", { name: "The Lighthouse" })).toBeInTheDocument();
      expect(within(picker).queryByRole("option", { name: "Mara" })).not.toBeInTheDocument();
    });

    it("adds a block and reports the picked card", async () => {
      const user = userEvent.setup();
      const onPick = vi.fn();
      render(
        <Harness questions={QUESTIONS} pickOptions={pickOptions} onPick={onPick} />,
      );
      await openQuestion(user, "Where");

      await user.selectOptions(
        screen.getByLabelText("Where can the player usually find them?"),
        "place-1",
      );

      expect(screen.getByText("Found at ↔")).toBeInTheDocument();
      expect(screen.getByText("The Lighthouse", { selector: "p" })).toBeInTheDocument();
      expect(onPick).toHaveBeenCalledWith(
        expect.objectContaining({ id: "found-at" }),
        pickOptions[0],
      );
    });

    it("reports the removal when a picked block is deleted", async () => {
      const user = userEvent.setup();
      const onRemovePick = vi.fn();
      const initial: LoreDocument = {
        blocks: [
          { kind: "answer", question_id: "found-at", label: "Found at", text: "The Lighthouse" },
        ],
      };
      render(
        <Harness
          initial={initial}
          questions={QUESTIONS}
          pickOptions={pickOptions}
          onRemovePick={onRemovePick}
        />,
      );

      await user.click(screen.getByRole("button", { name: "Found at options" }));
      await user.click(screen.getByRole("menuitem", { name: /delete/i }));

      expect(onRemovePick).toHaveBeenCalledWith(
        expect.objectContaining({ id: "found-at" }),
        "The Lighthouse",
      );
      expect(screen.queryByText("Found at ↔")).not.toBeInTheDocument();
    });

    it("shows Missing when the picked card no longer exists", () => {
      const initial: LoreDocument = {
        blocks: [
          { kind: "answer", question_id: "found-at", label: "Found at", text: "The Docks" },
        ],
      };
      render(
        <Harness initial={initial} questions={QUESTIONS} pickOptions={pickOptions} />,
      );

      expect(screen.getByText("Missing: The Docks")).toBeInTheDocument();
    });
  });
});
