import { useState } from "react";
import { NEW_NUMBER_DEFAULTS } from "../constants/sentenceBuilder";
import type { ValueKind } from "../types/sentence.types";
import type { NewTrackedValue } from "../types/trackedValue.types";

const splitChoices = (raw: string): string[] =>
  raw
    .split(",")
    .map((choice) => choice.trim())
    .filter(Boolean);

const toNumber = (raw: string, fallback: number): number => {
  const parsed = Number(raw);
  return raw.trim() !== "" && Number.isFinite(parsed) ? parsed : fallback;
};

export interface NewValueForm {
  fields: { name: string; kind: ValueKind; startsAt: string; lowest: string; highest: string; choices: string };
  setters: {
    setName: (value: string) => void;
    setKind: (value: ValueKind) => void;
    setStartsAt: (value: string) => void;
    setLowest: (value: string) => void;
    setHighest: (value: string) => void;
    setChoices: (value: string) => void;
  };
  isComplete: boolean;
  buildInput: () => NewTrackedValue;
}

export const useNewValueForm = (): NewValueForm => {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ValueKind>("number");
  const [startsAt, setStartsAt] = useState(String(NEW_NUMBER_DEFAULTS.initial));
  const [lowest, setLowest] = useState(String(NEW_NUMBER_DEFAULTS.min));
  const [highest, setHighest] = useState(String(NEW_NUMBER_DEFAULTS.max));
  const [choices, setChoices] = useState("");
  const choiceList = splitChoices(choices);
  const isComplete = name.trim() !== "" && (kind !== "enum" || choiceList.length > 0);

  const buildInput = (): NewTrackedValue => {
    if (kind === "boolean") return { name, kind };
    if (kind === "enum") return { name, kind, options: choiceList };
    return {
      name,
      kind,
      initial: toNumber(startsAt, NEW_NUMBER_DEFAULTS.initial),
      min: toNumber(lowest, NEW_NUMBER_DEFAULTS.min),
      max: toNumber(highest, NEW_NUMBER_DEFAULTS.max),
    };
  };

  return {
    fields: { name, kind, startsAt, lowest, highest, choices },
    setters: { setName, setKind, setStartsAt, setLowest, setHighest, setChoices },
    isComplete,
    buildInput,
  };
};
