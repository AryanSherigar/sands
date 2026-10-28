import React, { useEffect, useMemo, useRef, useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import {
  ADD_WHAT_HAPPENS_MESSAGE,
  DELETE_LABEL,
  DUPLICATE_LABEL,
  MISSING_VALUE_BLOCK_MESSAGE,
  TEST_RULE_LABEL,
} from "../../../constants/advancedCards";
import {
  EVERY_TURN_HELP,
  EVERY_TURN_LABEL,
  ONLY_ONCE_LABEL,
  SOUND_ENABLE_FAILED_MESSAGE,
} from "../../../constants/rules";
import { findMissingChangePaths, findUnsupportedChangePaths } from "../../../lib/changeRows";
import { useEnsureTool } from "../../../hooks/useEnsureTool";
import { useOpenFullEditor } from "../../../hooks/useOpenFullEditor";
import { useRowAutosave } from "../../../hooks/useRowAutosave";
import { useTestSentence } from "../../../hooks/useTestSentence";
import { useValueOptionsState } from "../../../hooks/useValueOptionsState";
import {
  buildAutoTitle,
  buildLabelMap,
  buildRuleDraft,
  buildRulePatch,
  findSelfRepeatMessage,
  isThenEmpty,
  type RuleDraft,
  type SoundDraft,
} from "../../../lib/ruleDraft";
import { parseExpression } from "../../../lib/sentenceCompiler";
import { SentenceBuilder } from "../../SentenceBuilder/SentenceBuilder";
import type { RuleCardProps } from "./Advanced.types";
import { AdvancedCard } from "./AdvancedCard";
import { ComparisonFitNote } from "./ComparisonFitNote";
import { FieldBlock } from "./FieldBlock";
import { ThenActions } from "./ThenActions";

const FREQUENCY_OPTIONS = [
  { isOneShot: false, label: EVERY_TURN_LABEL },
  { isOneShot: true, label: ONLY_ONCE_LABEL },
];

export const RuleCard: React.FC<RuleCardProps> = ({ rule, index, onUpdate, onDuplicate, onDelete, onSoundRemoved }) => {
  const { options, isUnsupportedPath } = useValueOptionsState();
  const openFullEditor = useOpenFullEditor();
  const testSentence = useTestSentence();
  const { ensureTool } = useEnsureTool();
  const showToast = useToast();
  const [isValid, setIsValid] = useState(true);
  const [hasTouchedThen, setHasTouchedThen] = useState(false);
  const serverDraft = useMemo(() => buildRuleDraft(rule, options), [options, rule]);
  const { value: draft, commit, flush } = useRowAutosave<RuleDraft>({
    serverDraft,
    save: (next) => {
      if (isThenEmpty(next)) return;
      const patch = buildRulePatch(rule, next, options, {
        isExpressionBlocked: !isValid,
        isChangesBlocked:
          findMissingChangePaths(next.changes, options, isUnsupportedPath).length > 0 ||
          findUnsupportedChangePaths(next.changes, isUnsupportedPath).length > 0,
      });
      if (Object.keys(patch).length > 0) onUpdate(patch);
    },
  });
  const draftRef = useRef(draft);
  useEffect(() => {
    draftRef.current = draft;
  });
  const labels = buildLabelMap(options);
  const autoTitle = buildAutoTitle(draft.expression, draft.metadata, labels);
  const repeatMessage = findSelfRepeatMessage(draft, options);
  const label = `Rule ${index + 1}`;
  const shouldAskForThen = isThenEmpty(draft) && (hasTouchedThen || draft.expression !== null);

  const enableAtmosphere = async (): Promise<boolean> => {
    try {
      await ensureTool("atmosphere");
      return true;
    } catch (error) {
      logEvent("warning", "atmosphere_enable_failed", { error: String(error) });
      showToast(SOUND_ENABLE_FAILED_MESSAGE, "error");
      return false;
    }
  };
  const handleChange = (next: RuleDraft): void => {
    setHasTouchedThen(true);
    commit(next);
  };
  const handleSoundChange = async (next: SoundDraft): Promise<void> => {
    const hadSound = draftRef.current.sound.cue !== "";
    if (next.cue && !hadSound && !(await enableAtmosphere())) return;
    commit({ ...draftRef.current, sound: next });
    if (hadSound && !next.cue) onSoundRemoved();
  };
  const handleTest = (): void => {
    flush();
    testSentence({
      kind: "rule",
      sentence: draft.expression ? parseExpression(draft.expression, draft.metadata) : null,
    });
  };
  const menuItems: OverflowMenuItem[] = [
    { id: "duplicate", label: DUPLICATE_LABEL, onSelect: onDuplicate },
    { id: "test", label: TEST_RULE_LABEL, onSelect: handleTest },
    { id: "delete", label: DELETE_LABEL, isDanger: true, onSelect: onDelete },
  ];

  return (
    <AdvancedCard ariaLabel={label} badge={label} menuLabel={`${label} options`} menuItems={menuItems}>
      <label className="block space-y-1 text-meta font-medium text-content-muted">
        Title
        <Input
          value={draft.title}
          placeholder={autoTitle ?? "Name this rule"}
          onChange={(event) => handleChange({ ...draft, title: event.target.value })}
        />
      </label>
      <FieldBlock label="When">
        <SentenceBuilder
          value={draft.expression}
          metadata={draft.metadata}
          onChange={(next) =>
            handleChange({ ...draft, expression: next?.expression ?? null, metadata: next?.metadata })
          }
          onOpenFullEditor={openFullEditor}
          onValidityChange={setIsValid}
        />
        {!isValid && <p className="text-meta text-danger">{MISSING_VALUE_BLOCK_MESSAGE}</p>}
        <ComparisonFitNote expression={draft.expression} metadata={draft.metadata} options={options} />
      </FieldBlock>
      <fieldset className="space-y-1.5">
        <legend className="text-meta font-medium text-content-muted">How often</legend>
        {FREQUENCY_OPTIONS.map((option) => (
          <label key={option.label} className="flex items-center gap-2 text-body text-content">
            <input
              type="radio"
              name={`${rule.condition_id}-frequency`}
              checked={draft.isOneShot === option.isOneShot}
              onChange={() => handleChange({ ...draft, isOneShot: option.isOneShot })}
            />
            {option.label}
          </label>
        ))}
        <p className="text-micro text-content-faint">{EVERY_TURN_HELP}</p>
      </fieldset>
      <ThenActions draft={draft} options={options} onChange={handleChange} onSoundChange={(next) => void handleSoundChange(next)} />
      {shouldAskForThen && (
        <p role="alert" className="text-meta text-danger">
          {ADD_WHAT_HAPPENS_MESSAGE}
        </p>
      )}
      {repeatMessage && <p role="status" className="text-meta text-warning">{repeatMessage}</p>}
    </AdvancedCard>
  );
};
