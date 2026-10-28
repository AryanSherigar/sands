import { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Modal } from "@/shared/components/ui/Modal";
import {
  HORROR_EXPERIENCE_OPTIONS,
  USUAL_DEVICE_OPTIONS,
} from "@/shared/constants/alpha-survey";
import { useSubmitSurvey } from "@/shared/hooks/useSubmitSurvey";
import type {
  HorrorExperience,
  UsualDevice,
} from "@/shared/types/alphaSurvey.types";
import type { IntakeSurveyProps } from "./IntakeSurvey.types";

export function IntakeSurvey({ isOpen, onClose }: IntakeSurveyProps) {
  const [experience, setExperience] = useState<HorrorExperience | "">("");
  const [device, setDevice] = useState<UsualDevice | "">("");
  const { mutate, isPending } = useSubmitSurvey();
  const canSubmit = experience !== "" && device !== "";

  const handleSubmit = (): void => {
    if (experience === "" || device === "") return;
    mutate(
      {
        kind: "intake",
        answers: { horror_experience: experience, usual_device: device },
      },
      { onSettled: onClose },
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Two quick questions" isSheetOnMobile>
      <div className="space-y-5">
        <label className="block space-y-2 text-sm text-content">
          <span>How much horror do you usually play or watch?</span>
          <select
            value={experience}
            onChange={(event) =>
              setExperience(event.target.value as HorrorExperience | "")
            }
            className="min-h-11 w-full rounded-md border border-border-strong bg-surface-raised px-3 text-content"
          >
            <option value="">Choose one</option>
            {HORROR_EXPERIENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-2 text-sm text-content">
          <span>What do you usually play on?</span>
          <select
            value={device}
            onChange={(event) => setDevice(event.target.value as UsualDevice | "")}
            className="min-h-11 w-full rounded-md border border-border-strong bg-surface-raised px-3 text-content"
          >
            <option value="">Choose one</option>
            {USUAL_DEVICE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={onClose}>
            Skip
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || isPending}>
            Send
          </Button>
        </div>
      </div>
    </Modal>
  );
}
