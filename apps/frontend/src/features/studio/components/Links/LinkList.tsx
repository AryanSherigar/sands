import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { getLinkSuggestions } from "../../lib/cardLinks";
import { getCardKind } from "../../lib/cardKind";
import { AddLinkForm } from "./AddLinkForm";
import { LinkRow } from "./LinkRow";
import type { NewLinkInput } from "../../types/fact.types";
import type { LinkListProps } from "./Links.types";

export const LinkList: React.FC<LinkListProps> = ({
  entityId,
  entityName,
  entityKind,
  links,
  candidates,
  errorMessage,
  isAdvanced = false,
  onCreate,
  onChangeWhen,
  onChangePredicate,
  onToggleSecret,
  onDelete,
  onOpenCard,
}) => {
  const [isAdding, setIsAdding] = useState(false);

  const handleOpenForm = (): void => setIsAdding(true);
  const handleCloseForm = (): void => setIsAdding(false);
  const handleSubmit = (input: NewLinkInput): void => {
    onCreate(input);
    setIsAdding(false);
  };

  return (
    <section aria-label="Links" className="space-y-2">
      <h3 className="text-meta font-medium text-content-muted">Links</h3>
      {links.length > 0 && (
        <ul className="space-y-2">
          {links.map((view) => (
            <LinkRow
              key={view.fact.fact_id}
              view={view}
              currentEntityId={entityId}
              suggestions={getLinkSuggestions(
                view.subject ? getCardKind(view.subject.entity_type) : entityKind,
                view.object ? getCardKind(view.object.entity_type) : "other",
              )}
              isAdvanced={isAdvanced}
              onChangeWhen={onChangeWhen}
              onChangePredicate={onChangePredicate}
              onToggleSecret={onToggleSecret}
              onDelete={onDelete}
              onOpenCard={onOpenCard}
            />
          ))}
        </ul>
      )}
      {errorMessage && <p className="text-micro text-danger">{errorMessage}</p>}
      {isAdding && (
        <AddLinkForm
          subjectName={entityName}
          subjectKind={entityKind}
          candidates={candidates}
          isAdvanced={isAdvanced}
          onSubmit={handleSubmit}
          onCancel={handleCloseForm}
        />
      )}
      {!isAdding && (
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={candidates.length === 0 && !isAdvanced}
          onClick={handleOpenForm}
        >
          Add link
        </Button>
      )}
    </section>
  );
};
