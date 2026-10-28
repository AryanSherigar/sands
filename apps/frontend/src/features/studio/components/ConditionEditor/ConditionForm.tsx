import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { ExpressionBuilder } from "./ExpressionBuilder/ExpressionBuilder";
import { FieldExpression } from "./ExpressionBuilder/ExpressionBuilder.types";
import { StateMutation } from "../../types/condition.types";
import { CueSection } from "./CueSection";
import { DEFAULT_SILENCE_DURATION_MS } from "../../constants/condition";
import { StateMutationList } from "./StateMutationList";
import { ConditionFormProps } from "./ConditionForm.types";

interface ConditionFormState {
  label: string;
  narratorInstruction: string;
  conditionExpression: FieldExpression | null;
  stateMutations: StateMutation[];
  isOneShot: boolean;
  cue: string;
  cutAmbient: boolean;
  silenceMs: number;
}

const readInitialMutations = (
  condition: ConditionFormProps["condition"],
): StateMutation[] => {
  if (condition?.state_mutations?.length) return condition.state_mutations;
  return condition?.state_mutation ? [condition.state_mutation] : [];
};

const buildInitialState = (
  condition: ConditionFormProps["condition"],
): ConditionFormState => ({
  label: condition?.label ?? "",
  narratorInstruction: condition?.narrator_instruction ?? "",
  conditionExpression:
    (condition?.condition_expression as FieldExpression | undefined) ?? null,
  stateMutations: readInitialMutations(condition),
  isOneShot: condition?.is_one_shot ?? false,
  cue: condition?.sensory_cue ?? "",
  cutAmbient: condition?.cut_ambient ?? true,
  silenceMs: condition?.silence_duration_ms ?? DEFAULT_SILENCE_DURATION_MS,
});

export const ConditionForm: React.FC<ConditionFormProps> = ({
  condition,
  availableFields,
  onSubmit,
  onCancel,
  hasAtmosphere = false,
  isSubmitting,
  submitError,
}) => {
  const [formState, setFormState] = useState<ConditionFormState>(() =>
    buildInitialState(condition),
  );

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    onSubmit({
      label: formState.label,
      narrator_instruction: formState.narratorInstruction,
      condition_expression:
        (formState.conditionExpression as unknown as Record<string, unknown>) ??
        undefined,
      state_mutations: formState.stateMutations,
      is_one_shot: formState.isOneShot,
      ...(hasAtmosphere
        ? {
            sensory_cue: formState.cue || null,
            cut_ambient: formState.cutAmbient,
            silence_duration_ms: formState.silenceMs,
          }
        : {}),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <Input
        value={formState.label}
        onChange={(e) => setFormState({ ...formState, label: e.target.value })}
        placeholder="Label"
        required
      />
      <textarea
        value={formState.narratorInstruction}
        onChange={(e) =>
          setFormState({ ...formState, narratorInstruction: e.target.value })
        }
        placeholder="Narrator instruction"
        className="rounded-md w-full border border-border-subtle bg-surface px-3 py-2 text-sm text-content-muted"
        rows={2}
        required
      />
      <ExpressionBuilder
        value={formState.conditionExpression}
        onChange={(expr) =>
          setFormState({ ...formState, conditionExpression: expr })
        }
        availableFields={availableFields}
      />
      <StateMutationList
        value={formState.stateMutations}
        onChange={(mutations) =>
          setFormState({ ...formState, stateMutations: mutations })
        }
      />
      <label className="flex items-center gap-2 text-sm text-content-muted">
        <input
          type="checkbox"
          checked={formState.isOneShot}
          onChange={(event) =>
            setFormState({ ...formState, isOneShot: event.target.checked })
          }
        />
        Fire only once
      </label>
      {hasAtmosphere && (
        <CueSection
          value={{
            cue: formState.cue,
            cutAmbient: formState.cutAmbient,
            silenceMs: formState.silenceMs,
          }}
          onChange={(cueValue) =>
            setFormState({
              ...formState,
              cue: cueValue.cue,
              cutAmbient: cueValue.cutAmbient,
              silenceMs: cueValue.silenceMs,
            })
          }
        />
      )}
      {submitError && <p className="text-xs text-danger">{submitError}</p>}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
};
