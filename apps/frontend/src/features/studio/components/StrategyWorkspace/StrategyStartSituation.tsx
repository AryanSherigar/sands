import React from "react";
import { START_PANELS, summarizePanel } from "../../lib/strategyPanels";
import { StrategyPresetPicker } from "./StrategyPresetPicker";
import { StrategyStartPanelBody } from "./StrategyStartPanelBody";
import type { StrategyStartSituationProps } from "./StrategyWorkspace.types";

export const StrategyStartSituation: React.FC<StrategyStartSituationProps> = ({
  fields,
  regions,
  openPanel,
  onOpenPanel,
  onEdit,
}) => (
  <section className="space-y-3">
    <h2 className="text-lg font-semibold">4. Starting situation</h2>
    <p className="text-sm text-content-muted">Everything here has a default. Open a section only to change it.</p>
    <StrategyPresetPicker fields={fields} regions={regions} onEdit={onEdit} />
    <ul className="space-y-2">
      {START_PANELS.map((panel) => {
        const isOpen = openPanel === panel.id;
        return (
          <li key={panel.id} className="rounded-md border border-border-subtle bg-surface-raised">
            <button
              type="button"
              aria-expanded={isOpen}
              className="flex w-full items-center justify-between p-3 text-left text-sm font-medium"
              onClick={() => onOpenPanel(isOpen ? null : panel.id)}
            >
              <span>{panel.label}</span>
              <span className="text-content-muted">{summarizePanel(panel.id, fields)}</span>
            </button>
            {isOpen && (
              <div className="border-t border-border-subtle p-3">
                <StrategyStartPanelBody panelId={panel.id} fields={fields} regions={regions} onEdit={onEdit} />
              </div>
            )}
          </li>
        );
      })}
    </ul>
  </section>
);
