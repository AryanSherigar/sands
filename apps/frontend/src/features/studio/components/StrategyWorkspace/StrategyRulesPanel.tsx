import React from "react";
import {
  BUILTIN_DISASTER_OPTIONS,
  MAX_CONDITIONAL_PERCENT,
  MAX_PERCENT,
} from "../../constants/strategyAuthoring";
import { setRules } from "../../lib/strategyRules";
import type {
  StrategyRules,
  StrategySystemToggles,
} from "../../types/strategyDocument.types";
import { StrategyNumberField } from "./StrategyNumberField";
import type { StrategyRulesPanelProps } from "./StrategyWorkspace.types";

interface RuleField {
  key: keyof StrategyRules;
  label: string;
  max?: number;
}

const TREATY_FIELDS: readonly RuleField[] = [
  { key: "trade_value_per_turn", label: "Trade deal value per turn" },
  { key: "trade_income_percent", label: "Trade income bonus (%)" },
  { key: "access_value_per_turn", label: "Military access value per turn" },
  { key: "conditional_trigger_percent", label: "Trigger clause weight (%)", max: MAX_CONDITIONAL_PERCENT },
  { key: "conditional_gate_percent", label: "Gate clause weight (%)", max: MAX_CONDITIONAL_PERCENT },
];

const OATH_FIELDS: readonly RuleField[] = [
  { key: "oath_offer_min_opinion", label: "Opinion needed before a realm offers an oath" },
  { key: "oath_offer_duration_turns", label: "Length of an offered oath (turns)" },
];

const SYSTEM_TOGGLE_OPTIONS: readonly { key: keyof StrategySystemToggles; label: string; desc: string }[] = [
  { key: "is_loans_enabled", label: "Moneylending & debt defaults", desc: "Allow factions to borrow from creditors" },
  { key: "is_events_enabled", label: "Periodic dilemma events", desc: "Random narrative events fire throughout campaign" },
  { key: "is_outrage_enabled", label: "Diplomatic outrage & infamy", desc: "Aggressive expansion causes diplomatic blowback" },
  { key: "is_overtures_enabled", label: "Dynamic overtures & gifts", desc: "Factions can send diplomatic overtures" },
  { key: "is_ai_peace_enabled", label: "AI factions can sue for peace", desc: "Uncheck to force a fight-to-the-death wargame" },
  { key: "is_ai_alliance_enabled", label: "AI defensive pacts & alliances", desc: "Allow AI factions to team up against rivals" },
  { key: "is_ai_vassal_enabled", label: "AI vassalage & subjugation", desc: "Allow AI factions to bend the knee or subjugate" },
  { key: "is_ai_pressure_enabled", label: "AI ultimatum demands & pressure", desc: "AI factions leverage strength to coerce rivals" },
  { key: "is_ai_subsidy_enabled", label: "AI subsidies & financial aid", desc: "AI factions can bankroll their allies" },
];

const PacingSection: React.FC<StrategyRulesPanelProps> = ({ fields, onEdit }) => (
  <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3">
    <h3 className="text-sm font-semibold text-content">Turn Pacing & Actions</h3>
    <div className="grid gap-3 sm:grid-cols-2">
      <StrategyNumberField
        label="Order points per turn"
        value={fields.orders_per_turn}
        max={20}
        onCommit={(orders_per_turn) =>
          onEdit((current) => ({ ...current, orders_per_turn: Math.max(1, orders_per_turn) }))
        }
      />
      <StrategyNumberField
        label="Event frequency (%)"
        value={fields.event_frequency_percent}
        max={MAX_PERCENT}
        onCommit={(event_frequency_percent) =>
          onEdit((current) => ({ ...current, event_frequency_percent }))
        }
      />
    </div>
  </div>
);

const DisastersSection: React.FC<StrategyRulesPanelProps> = ({ fields, onEdit }) => {
  const disabledSet = new Set(fields.disabled_builtin_event_ids);

  const handleToggle = (id: string, isAllowed: boolean): void => {
    onEdit((current) => {
      const next = isAllowed
        ? current.disabled_builtin_event_ids.filter((item) => item !== id)
        : [...current.disabled_builtin_event_ids, id];
      return { ...current, disabled_builtin_event_ids: next };
    });
  };

  return (
    <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3">
      <div>
        <h3 className="text-sm font-semibold text-content">Allowed Disasters & Crises</h3>
        <p className="text-xs text-content-muted">Uncheck any event archetypes that should never fire in this scenario.</p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {BUILTIN_DISASTER_OPTIONS.map((disaster) => (
          <label key={disaster.id} className="flex items-start gap-2 text-xs">
            <input
              type="checkbox"
              checked={!disabledSet.has(disaster.id)}
              onChange={(event) => handleToggle(disaster.id, event.target.checked)}
              className="mt-0.5"
            />
            <div>
              <span className="font-medium text-content">{disaster.label}</span>
              <p className="text-[11px] text-content-muted">{disaster.description}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

const SubsystemsSection: React.FC<StrategyRulesPanelProps> = ({ fields, onEdit }) => {
  const handleToggle = (key: keyof StrategySystemToggles, isChecked: boolean): void => {
    onEdit((current) => ({
      ...current,
      toggles: { ...current.toggles, [key]: isChecked },
    }));
  };

  return (
    <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3">
      <div>
        <h3 className="text-sm font-semibold text-content">Simulation Subsystems & AI Rules</h3>
        <p className="text-xs text-content-muted">Toggle core simulation mechanics and AI behavioral freedom.</p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {SYSTEM_TOGGLE_OPTIONS.map((option) => (
          <label key={option.key} className="flex items-start gap-2 text-xs">
            <input
              type="checkbox"
              checked={fields.toggles[option.key]}
              onChange={(event) => handleToggle(option.key, event.target.checked)}
              className="mt-0.5"
            />
            <div>
              <span className="font-medium text-content">{option.label}</span>
              <p className="text-[11px] text-content-muted">{option.desc}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

const TreatyParametersSection: React.FC<StrategyRulesPanelProps> = ({ fields, onEdit }) => {
  const { rules } = fields;

  const renderField = ({ key, label, max }: RuleField) => (
    <StrategyNumberField
      key={key}
      label={label}
      value={rules[key] as number}
      max={max}
      onCommit={(value) => onEdit((current) => setRules(current, { [key]: value }))}
    />
  );

  return (
    <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3">
      <h3 className="text-sm font-semibold text-content">Diplomacy & Espionage Tuning</h3>
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={rules.agents_enabled}
            onChange={(event) => {
              const isEnabled = event.target.checked;
              onEdit((current) => setRules(current, { agents_enabled: isEnabled }));
            }}
          />
          Unreliable spymasters report rumors
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={rules.revolt_talks_enabled}
            onChange={(event) => {
              const isEnabled = event.target.checked;
              onEdit((current) => setRules(current, { revolt_talks_enabled: isEnabled }));
            }}
          />
          Revolts can be talked down, with covenants to the people
        </label>
        <StrategyNumberField
          label="Base price to bribe a spymaster"
          value={rules.bribe_base_price}
          onCommit={(bribe_base_price) => onEdit((current) => setRules(current, { bribe_base_price }))}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">{TREATY_FIELDS.map(renderField)}</div>
      <div className="grid gap-3 sm:grid-cols-2">{OATH_FIELDS.map(renderField)}</div>
    </div>
  );
};

const LetterJudgmentSection: React.FC<StrategyRulesPanelProps> = ({ fields, onEdit }) => {
  const { rules } = fields;
  return (
    <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3">
      <h3 className="text-sm font-semibold text-content">Letters and Judgments</h3>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={rules.letters_enabled}
          onChange={(event) => {
            const isEnabled = event.target.checked;
            onEdit((current) => setRules(current, { letters_enabled: isEnabled }));
          }}
        />
        Rulers write letters to the player
      </label>
      {rules.letters_enabled && (
        <StrategyNumberField
          label="Turns between letters"
          value={rules.letter_cooldown_turns}
          onCommit={(letter_cooldown_turns) => onEdit((current) => setRules(current, { letter_cooldown_turns }))}
        />
      )}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={rules.judgments_enabled}
          onChange={(event) => {
            const isEnabled = event.target.checked;
            onEdit((current) => setRules(current, { judgments_enabled: isEnabled }));
          }}
        />
        The player judges prisoners and disputes in person
      </label>
      {rules.judgments_enabled && (
        <div className="grid gap-3 sm:grid-cols-2">
          <StrategyNumberField
            label="Turns between judgments"
            value={rules.judgment_cooldown_turns}
            onCommit={(judgment_cooldown_turns) => onEdit((current) => setRules(current, { judgment_cooldown_turns }))}
          />
          <StrategyNumberField
            label="Turns a sentence lasts"
            value={rules.judgment_sentence_turns}
            onCommit={(judgment_sentence_turns) => onEdit((current) => setRules(current, { judgment_sentence_turns }))}
          />
        </div>
      )}
    </div>
  );
};

export const StrategyRulesPanel: React.FC<StrategyRulesPanelProps> = (props) => (
  <div className="space-y-4">
    <PacingSection {...props} />
    <DisastersSection {...props} />
    <SubsystemsSection {...props} />
    <TreatyParametersSection {...props} />
    <LetterJudgmentSection {...props} />
  </div>
);
