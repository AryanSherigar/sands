import React from "react";
import { PLAYTEST_READOUT_LABEL } from "../../constants/playtest";
import { useGuide } from "../../hooks/useGuide";
import { useValueOptions } from "../../hooks/useValueOptions";
import { buildReadoutRows, listHiddenPaths } from "../../lib/stateReadout";
import { usePlaytestStore } from "../../stores/playtest.store";

export const StateReadout: React.FC = () => {
  const { scenario } = useGuide();
  const options = useValueOptions();
  const state = usePlaytestStore((store) => store.state);
  const hiddenPaths = listHiddenPaths(scenario?.state_schema ?? {});
  const rows = buildReadoutRows(options, state, hiddenPaths);

  if (scenario?.mode !== "master" || rows.length === 0) return null;
  return (
    <section
      aria-label={PLAYTEST_READOUT_LABEL}
      className="border-b border-border-subtle bg-surface-inset px-4 py-2"
    >
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-meta text-content-muted">
        {rows.map((row) => (
          <li key={row.path}>
            {row.label}: <span className="text-content">{row.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
};
