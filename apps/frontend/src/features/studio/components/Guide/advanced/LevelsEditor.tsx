import React, { useEffect, useRef, useState } from "react";
import { IconX } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import {
  findLevelProblem,
  nextLevelThreshold,
  sortLevelRows,
  toLevelRows,
  toValidTiers,
  type LevelRow,
} from "../../../lib/levels";
import type { LevelsEditorProps } from "./Advanced.types";
import { NumberField } from "./NumberField";

export const LevelsEditor: React.FC<LevelsEditorProps> = ({ tiers, onChange }) => {
  const [rows, setRows] = useState<LevelRow[]>(() => toLevelRows(tiers));
  const lastSent = useRef(JSON.stringify(tiers));
  const addedCount = useRef(0);
  const problem = findLevelProblem(rows);

  useEffect(() => {
    const incoming = JSON.stringify(tiers);
    if (incoming === lastSent.current) return;
    lastSent.current = incoming;
    setRows(toLevelRows(tiers));
  }, [tiers]);

  const update = (next: LevelRow[]): void => {
    setRows(next);
    const valid = toValidTiers(next);
    if (!valid) return;
    lastSent.current = JSON.stringify(valid);
    onChange(valid);
  };
  const patchRow = (id: string, patch: Partial<LevelRow>): void =>
    update(rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  const handleSort = (): void => setRows((current) => sortLevelRows(current));
  const handleAdd = (): void => {
    addedCount.current += 1;
    update([...rows, { id: `added-${addedCount.current}`, name: "New level", min: nextLevelThreshold(rows) }]);
  };

  return (
    <div className="space-y-2">
      <ul className="space-y-2">
        {rows.map((row, index) => (
          <li key={row.id} className="flex items-end gap-2">
            <label className="block flex-1 space-y-1 text-meta text-content-muted">
              {`Level ${index + 1} name`}
              <Input value={row.name} onChange={(event) => patchRow(row.id, { name: event.target.value })} />
            </label>
            <div className="w-28">
              <NumberField
                label={`Level ${index + 1} from`}
                value={row.min}
                placeholder="and below"
                onChange={(value) => patchRow(row.id, { min: value })}
                onBlur={handleSort}
              />
            </div>
            <button
              type="button"
              aria-label={`Remove level ${index + 1}`}
              onClick={() => update(rows.filter((other) => other.id !== row.id))}
              className="flex h-10 w-8 items-center justify-center rounded-md text-content-faint hover:bg-surface-overlay hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
            >
              <IconX size={14} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
      {problem && (
        <p role="alert" className="text-meta text-danger">
          {problem}
        </p>
      )}
      <Button type="button" variant="ghost" size="sm" onClick={handleAdd}>
        + Add a level
      </Button>
    </div>
  );
};
