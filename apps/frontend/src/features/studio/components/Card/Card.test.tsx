import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { createQueryWrapper } from "@/test/queryWrapper";
import {
  CARD_TEST_SCENARIO_ID,
  buildEntityFixture,
  buildFactFixture,
  installCardApi,
} from "../../test/cardApiMock";
import type { QuestionGroup } from "../../types/guide.types";
import { Card } from "./Card";
import type { CardProps } from "./Card.types";

const SAVE_TIMEOUT_MS = 4000;

const mara = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });
const lighthouse = buildEntityFixture({
  entity_id: "lighthouse",
  canonical_name: "The Lighthouse",
  entity_type: "location",
});
const tomas = buildEntityFixture({ entity_id: "tomas", canonical_name: "Tomas" });

const livesIn = buildFactFixture({
  fact_id: "f-lives",
  subject_entity_id: "mara",
  predicate: "lives in",
  object_entity_id: "lighthouse",
});

const WHERE_QUESTIONS: QuestionGroup[] = [
  {
    id: "where",
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

const renderCards = (...cards: Array<Partial<CardProps> & { entityId: string }>) => {
  const Wrapper = createQueryWrapper();
  return render(
    <Wrapper>
      {cards.map((card) => (
        <section key={card.entityId} aria-label={`card-${card.entityId}`}>
          <Card scenarioId={CARD_TEST_SCENARIO_ID} {...card} />
        </section>
      ))}
    </Wrapper>,
  );
};

const findCard = async (entityId: string) =>
  within(await screen.findByRole("region", { name: `card-${entityId}` }));

describe("Card", () => {
  it("shows the name as the first trigger and lets the creator remove it", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara], facts: [] });
    renderCards({ entityId: "mara" });
    const card = await findCard("mara");

    expect(await card.findByText("Mara", { selector: "span" })).toBeInTheDocument();
    await user.click(await card.findByRole("button", { name: "Remove trigger Mara" }));

    await waitFor(
      () => expect(api.entityUpdates.at(-1)?.body.aliases).toEqual([]),
      { timeout: SAVE_TIMEOUT_MS },
    );
  });

  it("adds a trigger with Enter and removes it with the cross", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara], facts: [] });
    renderCards({ entityId: "mara" });
    const card = await findCard("mara");

    await user.type(await card.findByLabelText("Add a trigger"), "the keeper{Enter}");
    expect(card.getByText("the keeper")).toBeInTheDocument();
    await waitFor(
      () => expect(api.entityUpdates.at(-1)?.body.aliases).toEqual(["Mara", "the keeper"]),
      { timeout: SAVE_TIMEOUT_MS },
    );

    await user.click(card.getByRole("button", { name: "Remove trigger the keeper" }));
    expect(card.queryByText("the keeper")).not.toBeInTheDocument();
  });

  it("renames the name trigger along with the card", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara], facts: [] });
    renderCards({ entityId: "mara" });
    const card = await findCard("mara");

    const nameInput = await card.findByLabelText("Name");
    await user.clear(nameInput);
    await user.type(nameInput, "Maria");

    await waitFor(
      () => {
        const body = api.entityUpdates.at(-1)?.body;
        expect(body?.canonical_name).toBe("Maria");
        expect(body?.aliases).toEqual(["Maria"]);
      },
      { timeout: SAVE_TIMEOUT_MS },
    );
  });

  it("saves the lore box as a lore document", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara], facts: [] });
    renderCards({ entityId: "mara" });
    const card = await findCard("mara");

    await user.type(await card.findByRole("textbox", { name: "About Mara" }), "Keeps the light.");

    await waitFor(
      () =>
        expect(api.entityUpdates.at(-1)?.body.lore_document).toEqual({
          blocks: [{ kind: "text", text: "Keeps the light." }],
        }),
      { timeout: SAVE_TIMEOUT_MS },
    );
  });

  it("shows one link on both cards and edits it from either side", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara, lighthouse], facts: [livesIn] });
    renderCards({ entityId: "mara" }, { entityId: "lighthouse" });
    const maraCard = await findCard("mara");
    const lighthouseCard = await findCard("lighthouse");

    const fromMara = await maraCard.findByLabelText("How Mara and The Lighthouse are linked");
    const fromLighthouse = await lighthouseCard.findByLabelText(
      "How Mara and The Lighthouse are linked",
    );
    expect(fromMara).toHaveValue("lives in");
    expect(fromLighthouse).toHaveValue("lives in");

    await user.clear(fromLighthouse);
    await user.type(fromLighthouse, "guards");
    await user.tab();

    await waitFor(() => expect(api.factUpdates.at(-1)).toEqual({
      factId: "f-lives",
      body: { predicate: "guards" },
    }));
    await waitFor(() =>
      expect(
        maraCard.getByLabelText("How Mara and The Lighthouse are linked"),
      ).toHaveValue("guards"),
    );
  });

  it("marks a link as Secret", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara, lighthouse], facts: [livesIn] });
    renderCards({ entityId: "mara" });
    const card = await findCard("mara");

    await user.click(await card.findByRole("button", { name: "Secret" }));

    await waitFor(() =>
      expect(api.factUpdates.at(-1)?.body).toEqual({ hidden: true }),
    );
    expect(await card.findByRole("button", { name: "Secret" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("accepts a free-text relationship when adding a link", async () => {
    const user = userEvent.setup();
    const api = installCardApi({ entities: [mara, tomas], facts: [] });
    renderCards({ entityId: "mara" });
    const card = await findCard("mara");

    await user.click(await card.findByRole("button", { name: "Add link" }));
    await user.selectOptions(card.getByLabelText("Link to"), "tomas");
    await user.type(card.getByLabelText("How are they linked?"), "owes a favour to");
    await user.click(card.getByRole("button", { name: "Save link" }));

    await waitFor(() =>
      expect(api.factCreates.at(-1)).toMatchObject({
        subject_entity_id: "mara",
        predicate: "owes a favour to",
        object_entity_id: "tomas",
      }),
    );
    expect(await card.findByDisplayValue("owes a favour to")).toBeInTheDocument();
  });

  it("lists the links before deleting a card and deletes on confirm", async () => {
    const user = userEvent.setup();
    const onDeleted = vi.fn();
    const facts = [
      livesIn,
      buildFactFixture({ fact_id: "f2", subject_entity_id: "tomas", predicate: "is the brother of", object_entity_id: "mara" }),
      buildFactFixture({ fact_id: "f3", subject_entity_id: "mara", predicate: "loves", object_entity_id: "tomas" }),
    ];
    const api = installCardApi({ entities: [mara, lighthouse, tomas], facts });
    renderCards({ entityId: "mara", onDeleted });
    const card = await findCard("mara");
    await card.findByLabelText("How Mara and The Lighthouse are linked");

    await user.click(card.getByRole("button", { name: "Mara options" }));
    await user.click(card.getByRole("menuitem", { name: /delete/i }));

    const dialog = within(await screen.findByRole("dialog"));
    expect(dialog.getByText("Mara has 3 links. Delete anyway?")).toBeInTheDocument();
    expect(dialog.getByText("Tomas is the brother of Mara")).toBeInTheDocument();
    await user.click(dialog.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(api.deletedEntityIds).toEqual(["mara"]));
    expect(onDeleted).toHaveBeenCalledWith("mara");
  });

  it("opens the other card when its name in a link is clicked", async () => {
    const user = userEvent.setup();
    const onOpenCard = vi.fn();
    installCardApi({ entities: [mara, lighthouse], facts: [livesIn] });
    renderCards({ entityId: "mara", onOpenCard });
    const card = await findCard("mara");

    await user.click(await card.findByRole("button", { name: "Open The Lighthouse" }));

    expect(onOpenCard).toHaveBeenCalledWith("lighthouse");
  });

  describe("pick questions", () => {
    const openWhere = async (
      user: ReturnType<typeof userEvent.setup>,
      card: ReturnType<typeof within>,
    ) => {
      await user.click(await card.findByRole("button", { name: /questions to help/i }));
      await user.click(card.getByRole("button", { name: "Where" }));
    };

    it("creates a link when a card is picked and removes it with the block", async () => {
      const user = userEvent.setup();
      const api = installCardApi({ entities: [mara, lighthouse], facts: [] });
      renderCards({ entityId: "mara", questions: WHERE_QUESTIONS });
      const card = await findCard("mara");
      await openWhere(user, card);

      await user.selectOptions(
        card.getByLabelText("Where can the player usually find them?"),
        "lighthouse",
      );

      await waitFor(() =>
        expect(api.factCreates.at(-1)).toMatchObject({
          subject_entity_id: "mara",
          predicate: "is usually found at",
          object_entity_id: "lighthouse",
        }),
      );
      expect(
        await card.findByLabelText("How Mara and The Lighthouse are linked"),
      ).toHaveValue("is usually found at");

      await user.click(card.getByRole("button", { name: "Found at options" }));
      await user.click(card.getByRole("menuitem", { name: /delete/i }));

      await waitFor(() => expect(api.deletedFactIds).toEqual(["fact-1"]));
    });

    it("removes the block when its link is deleted from the Links list", async () => {
      const user = userEvent.setup();
      const pickFact = buildFactFixture({
        fact_id: "f-pick",
        subject_entity_id: "mara",
        predicate: "is usually found at",
        object_entity_id: "lighthouse",
      });
      const picked = buildEntityFixture({
        entity_id: "mara",
        canonical_name: "Mara",
        lore_document: {
          blocks: [
            { kind: "answer", question_id: "found-at", label: "Found at", text: "The Lighthouse" },
          ],
        },
      });
      const api = installCardApi({ entities: [picked, lighthouse], facts: [pickFact] });
      renderCards({ entityId: "mara", questions: WHERE_QUESTIONS });
      const card = await findCard("mara");
      expect(await card.findByText("Found at ↔")).toBeInTheDocument();

      await user.click(
        card.getByRole("button", { name: "Remove link between Mara and The Lighthouse" }),
      );

      await waitFor(() => expect(api.deletedFactIds).toEqual(["f-pick"]));
      await waitFor(() => expect(card.queryByText("Found at ↔")).not.toBeInTheDocument());
    });

    it("shows Missing when the picked card was deleted", async () => {
      const picked = buildEntityFixture({
        entity_id: "mara",
        canonical_name: "Mara",
        lore_document: {
          blocks: [
            { kind: "answer", question_id: "found-at", label: "Found at", text: "The Docks" },
          ],
        },
      });
      installCardApi({ entities: [picked, lighthouse], facts: [] });
      renderCards({ entityId: "mara", questions: WHERE_QUESTIONS });
      const card = await findCard("mara");

      expect(await card.findByText("Missing: The Docks")).toBeInTheDocument();
    });
  });
});
