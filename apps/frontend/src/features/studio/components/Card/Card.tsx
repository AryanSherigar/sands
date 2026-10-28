import React, { useId, useMemo } from "react";
import { Input } from "@/shared/components/ui/Input";
import { SaveStatusIndicator } from "../SaveStatusIndicator/SaveStatusIndicator";
import { CARD_DEFAULT_NAME_LABEL } from "../../constants/card";
import { CARD_KIND_LABELS } from "../../constants/cardKinds";
import { useCardCommands } from "../../hooks/useCardCommands";
import { useCardDraft } from "../../hooks/useCardDraft";
import { useCardLinks } from "../../hooks/useCardLinks";
import { useCardPickLinks } from "../../hooks/useCardPickLinks";
import { useEntities } from "../../hooks/useEntities";
import { useIsAdvancedMode } from "../../hooks/useIsAdvancedMode";
import { getCardKind } from "../../lib/cardKind";
import { describeLink } from "../../lib/cardLinks";
import type { PickOption } from "../../types/guide.types";
import { LinkList } from "../Links/LinkList";
import { FeatureAnchor } from "../NewFeatures/FeatureAnchor";
import { LoreBox } from "../LoreBox/LoreBox";
import type { CardProps } from "./Card.types";
import { CardMenu } from "./CardMenu";
import { CardValues } from "./CardValues";
import { DeleteCardDialog } from "./DeleteCardDialog";
import { TriggerChips } from "./TriggerChips";

const NO_QUESTIONS: NonNullable<CardProps["questions"]> = [];

export const Card: React.FC<CardProps> = ({
  scenarioId,
  entityId,
  questions = NO_QUESTIONS,
  typeLabel,
  onOpenCard,
  onDeleted,
  onAddToAlwaysRemember,
}) => {
  const nameFieldId = useId();
  const { createEntityAsync, updateEntityAsync, deleteEntityAsync } =
    useEntities(scenarioId);
  const isAdvanced = useIsAdvancedMode();
  const cardLinks = useCardLinks(scenarioId, entityId, isAdvanced);
  const entity = cardLinks.entities.find((item) => item.entity_id === entityId);
  const cardDraft = useCardDraft(entity, (payload) =>
    updateEntityAsync({ entityId, payload }),
  );
  const pickLinks = useCardPickLinks({
    entityId,
    questions,
    facts: cardLinks.facts,
    entities: cardLinks.entities,
    lore: cardDraft.draft?.lore,
    setLore: cardDraft.setLore,
    createLink: cardLinks.createLink,
    deleteLink: cardLinks.deleteLink,
  });
  const commands = useCardCommands({
    entity,
    createEntity: createEntityAsync,
    deleteEntity: deleteEntityAsync,
    onDeleted,
  });
  const otherCards = useMemo(
    () => cardLinks.entities.filter((item) => item.entity_id !== entityId),
    [cardLinks.entities, entityId],
  );
  const pickOptions = useMemo(
    (): PickOption[] =>
      otherCards.map((item) => ({
        id: item.entity_id,
        name: item.canonical_name,
        kind: getCardKind(item.entity_type),
      })),
    [otherCards],
  );

  const { draft } = cardDraft;
  if (!entity || !draft) return null;
  const kind = getCardKind(entity.entity_type);
  const displayName = draft.name.trim() || CARD_DEFAULT_NAME_LABEL;

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void =>
    cardDraft.setName(event.target.value);
  const handleOpenInTab = onOpenCard ? () => onOpenCard(entityId) : undefined;

  return (
    <article className="space-y-4 rounded-lg border border-border-subtle bg-surface-raised p-4">
      <header className="flex items-center gap-2">
        <span className="rounded-sm border border-border-strong px-2 py-0.5 text-micro text-content-muted">
          {typeLabel ?? CARD_KIND_LABELS[kind]}
        </span>
        {cardDraft.hasError && (
          <span className="text-micro">
            <SaveStatusIndicator
              isSaving={false}
              lastSaved={null}
              hasError
              onRetry={cardDraft.retry}
            />
          </span>
        )}
        <div className="ml-auto">
          <CardMenu
            name={draft.name}
            onOpenInTab={handleOpenInTab}
            onDuplicate={commands.duplicate}
            onDelete={commands.openDelete}
          />
        </div>
      </header>
      <div className="space-y-1">
        <label htmlFor={nameFieldId} className="block text-meta font-medium text-content-muted">
          Name
        </label>
        <Input id={nameFieldId} value={draft.name} onChange={handleNameChange} />
      </div>
      <LoreBox
        document={draft.lore}
        onChange={cardDraft.setLore}
        ariaLabel={`About ${displayName}`}
        questions={questions}
        pickOptions={pickOptions}
        onPick={pickLinks.handlePick}
        onRemovePick={pickLinks.handleRemovePick}
        onAddToAlwaysRemember={onAddToAlwaysRemember}
      />
      <FeatureAnchor featureId="triggers">
        <TriggerChips
          name={draft.name}
          triggers={draft.aliases}
          onAdd={cardDraft.addTrigger}
          onRemove={cardDraft.removeTrigger}
        />
      </FeatureAnchor>
      {isAdvanced && <CardValues scenarioId={scenarioId} entity={entity} />}
      <FeatureAnchor featureId="links">
        <LinkList
          entityId={entityId}
          entityName={displayName}
          entityKind={kind}
          links={cardLinks.links}
          candidates={otherCards}
          errorMessage={cardLinks.errorMessage}
          isAdvanced={isAdvanced}
          onCreate={cardLinks.createLinkFrom}
          onChangeWhen={cardLinks.setWhenActive}
          onChangePredicate={cardLinks.updatePredicate}
          onToggleSecret={cardLinks.setSecret}
          onDelete={pickLinks.handleDeleteLink}
          onOpenCard={onOpenCard}
        />
      </FeatureAnchor>
      <DeleteCardDialog
        isOpen={commands.isDeleteOpen}
        cardName={displayName}
        linkSentences={cardLinks.links.map(describeLink)}
        isDeleting={commands.isDeleting}
        onConfirm={commands.confirmDelete}
        onCancel={commands.closeDelete}
      />
    </article>
  );
};
