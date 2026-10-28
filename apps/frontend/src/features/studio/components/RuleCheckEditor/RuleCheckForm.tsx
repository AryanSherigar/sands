import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import type { RuleCheckKind } from "@/shared/types/check.types";
import { RULE_CHECK_KIND_OPTIONS } from "../../constants/ruleCheck";
import { enumOptionValues } from "../../lib/stateSchemaFields";
import { ExpressionBuilder } from "../ConditionEditor/ExpressionBuilder/ExpressionBuilder";
import { RecallFields } from "./RecallFields";
import { RuleCheckFormProps } from "./RuleCheckForm.types";
import { RuleCheckPreview } from "./RuleCheckPreview";
import {
  RuleCheckFormState,
  buildInitialState,
  buildPayload,
  getFormProblems,
} from "./ruleCheckFormState";
import { TimedChoiceFields } from "./TimedChoiceFields";

const NO_FIELD_OPTION = { value: "", label: "Choose a tracked value" };

export const RuleCheckForm: React.FC<RuleCheckFormProps> = ({
  check,
  availableFields,
  enumFields,
  onSubmit,
  onCancel,
  isSubmitting,
  submitError,
}) => {
  const [state, setState] = useState<RuleCheckFormState>(() =>
    buildInitialState(check),
  );
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const resultChoices = enumOptionValues(
    enumFields.find((field) => field.path === state.resultPath)?.definition
      .options,
  );
  const problems = getFormProblems(state, resultChoices);
  const fieldOptions = [
    NO_FIELD_OPTION,
    ...enumFields.map((field) => ({
      value: field.path,
      label: `${field.label} (${field.path})`,
    })),
  ];

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (problems.length === 0) onSubmit(buildPayload(state));
  };

  const handleKindChange = (event: React.ChangeEvent<HTMLSelectElement>): void =>
    setState({ ...state, kind: event.target.value as RuleCheckKind });

  const handleResultPathChange = (
    event: React.ChangeEvent<HTMLSelectElement>,
  ): void => setState({ ...state, resultPath: event.target.value });

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        aria-label="Name"
        value={state.label}
        onChange={(event) => setState({ ...state, label: event.target.value })}
        placeholder="Name, e.g. Lamp-out"
        required
      />
      <div>
        <p className="mb-1 text-sm text-content-muted">Kind</p>
        <Select
          aria-label="Kind"
          options={[...RULE_CHECK_KIND_OPTIONS]}
          value={state.kind}
          onChange={handleKindChange}
        />
      </div>
      <div>
        <p className="mb-1 text-sm text-content-muted">Opens when</p>
        <ExpressionBuilder
          value={state.trigger}
          onChange={(trigger) => setState({ ...state, trigger })}
          availableFields={availableFields}
        />
        <p className="mt-1 text-xs text-content-faint">
          The prompt opens each time this becomes true after being false.
        </p>
      </div>
      <div>
        <p className="mb-1 text-sm text-content-muted">Answer is stored in</p>
        <Select
          aria-label="Answer is stored in"
          options={fieldOptions}
          value={state.resultPath}
          onChange={handleResultPathChange}
        />
        {enumFields.length === 0 && (
          <p className="mt-1 text-xs text-warning">
            Add a tracked value of type Enum first; its options are the answers.
          </p>
        )}
      </div>
      {state.kind === "timed_choice" ? (
        <TimedChoiceFields
          value={state.timed}
          resultChoices={resultChoices}
          onChange={(timed) => setState({ ...state, timed })}
        />
      ) : (
        <RecallFields
          value={state.recall}
          resultChoices={resultChoices}
          onChange={(recall) => setState({ ...state, recall })}
        />
      )}
      <textarea
        aria-label="Narrator instruction after the answer"
        value={state.narratorTemplate}
        onChange={(event) =>
          setState({ ...state, narratorTemplate: event.target.value })
        }
        placeholder="Optional: what the narrator does after the answer. Use {result} and {label}."
        className="rounded-md w-full border border-border-subtle bg-surface px-3 py-2 text-sm text-content-muted"
        rows={2}
      />
      {problems.length > 0 && (
        <ul role="alert" className="list-disc pl-5 text-xs text-warning">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      {submitError && (
        <p role="alert" className="text-xs text-danger">
          {submitError}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button
          type="button"
          variant="secondary"
          onClick={() => setIsPreviewOpen(true)}
        >
          Preview prompt
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={problems.length > 0 || isSubmitting}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
      </div>
      {isPreviewOpen && (
        <RuleCheckPreview state={state} onClose={() => setIsPreviewOpen(false)} />
      )}
    </form>
  );
};
