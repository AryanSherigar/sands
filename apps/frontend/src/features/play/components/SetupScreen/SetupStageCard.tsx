import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { IconArrowRight } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { SetupStageCardProps } from "./SetupStageCard.types";
import {
  getArrayValue,
  getInitialFormValues,
  getScenarioIdentifier,
  normalizeSetupFields,
  validateSetupForm,
  formatSetupSummary,
} from "./setupStageUtils";
import { SetupFieldRenderer } from "./SetupFieldRenderer";
import { SetupStageHeader } from "./SetupStageHeader";
import { SetupStageEmptyState } from "./SetupStageEmptyState";

export type { SetupStageCardProps };

export const SetupStageCard: React.FC<SetupStageCardProps> = ({
  scenario,
  isSubmitting = false,
  submitLabel = "Start Adventure",
  onSubmit,
}) => {
  const setupFields = useMemo(() => normalizeSetupFields(scenario), [scenario]);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  const scenarioIdentifier = getScenarioIdentifier(scenario);

  useEffect(() => {
    setFormValues(getInitialFormValues(setupFields));
    setErrors({});
  }, [scenarioIdentifier, setupFields]);

  const handleChange = (fieldKey: string, value: unknown): void => {
    setFormValues((prev) => ({ ...prev, [fieldKey]: value }));
    if (errors[fieldKey]) {
      setErrors((prev) => {
        const copy = { ...prev };
        delete copy[fieldKey];
        return copy;
      });
    }
  };

  const handleMultiSelectToggle = (
    fieldKey: string,
    optionValue: string,
  ): void => {
    const currentList = getArrayValue(formValues[fieldKey]);
    const exists = currentList.includes(optionValue);
    const updated = exists
      ? currentList.filter((v) => v !== optionValue)
      : [...currentList, optionValue];
    handleChange(fieldKey, updated);
  };

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    const newErrors = validateSetupForm(setupFields, formValues);
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    const formattedPayload = formatSetupSummary(setupFields, formValues);
    onSubmit(formattedPayload, formValues);
  };

  return (
    <div className="w-full max-w-[640px] mx-auto bg-surface-raised border border-border-subtle p-6 sm:p-10 rounded-md relative z-10 space-y-8 shadow-float">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-[2px] bg-linear-to-r from-transparent via-(--accent) to-transparent" />

      <SetupStageHeader title={scenario.title} />

      <form onSubmit={handleSubmit} className="space-y-6">
        {setupFields.length === 0 ? (
          <SetupStageEmptyState />
        ) : (
          <div className="space-y-6">
            {setupFields.map((field) => (
              <SetupFieldRenderer
                key={field.key}
                field={field}
                value={formValues[field.key]}
                error={errors[field.key]}
                onChange={handleChange}
                onMultiSelectToggle={handleMultiSelectToggle}
              />
            ))}
          </div>
        )}

        <div className="pt-6 border-t border-border-subtle flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link
            to="/discover"
            className="w-full sm:w-auto px-4 py-2 font-sans text-sm text-content-muted hover:text-content transition-colors text-center"
          >
            ← Back to Discover
          </Link>

          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={isSubmitting}
            className="w-full sm:w-auto"
          >
            <span>{isSubmitting ? "Initiating..." : submitLabel}</span>
            <IconArrowRight size={18} stroke={1.5} aria-hidden="true" />
          </Button>
        </div>
      </form>
    </div>
  );
};
