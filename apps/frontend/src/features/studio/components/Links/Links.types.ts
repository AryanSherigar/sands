import type { CardKind } from "../../types/card.types";
import type { EntityResponse } from "../../types/entity.types";
import type { FactResponse, NewLinkInput } from "../../types/fact.types";
import type { LinkView } from "../../lib/cardLinks";

export interface LinkRowProps {
  view: LinkView;
  currentEntityId: string;
  suggestions: string[];
  isAdvanced?: boolean;
  onChangeWhen?: (fact: FactResponse, whenActive: Record<string, unknown> | null) => void;
  onChangePredicate: (fact: FactResponse, predicate: string) => void;
  onToggleSecret: (fact: FactResponse, isSecret: boolean) => void;
  onDelete: (fact: FactResponse) => void;
  onOpenCard?: (entityId: string) => void;
}

export interface AddLinkFormProps {
  subjectName: string;
  subjectKind: CardKind;
  candidates: EntityResponse[];
  isAdvanced?: boolean;
  onSubmit: (input: NewLinkInput) => void;
  onCancel: () => void;
}

export interface LinkListProps {
  entityId: string;
  entityName: string;
  entityKind: CardKind;
  links: LinkView[];
  candidates: EntityResponse[];
  errorMessage?: string | null;
  isAdvanced?: boolean;
  onCreate: (input: NewLinkInput) => void;
  onChangeWhen?: (fact: FactResponse, whenActive: Record<string, unknown> | null) => void;
  onChangePredicate: (fact: FactResponse, predicate: string) => void;
  onToggleSecret: (fact: FactResponse, isSecret: boolean) => void;
  onDelete: (fact: FactResponse) => void;
  onOpenCard?: (entityId: string) => void;
}

export interface LinkWhenFieldProps {
  whenActive: Record<string, unknown> | null;
  onChange: (whenActive: Record<string, unknown> | null) => void;
}
