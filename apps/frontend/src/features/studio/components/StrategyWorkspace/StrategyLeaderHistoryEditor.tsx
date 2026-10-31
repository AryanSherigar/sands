import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { draftRulerBackstory } from "../../api/strategy.api";
import { updateLeader } from "../../lib/strategyDocument";
import type { StrategyLeaderHistoryEditorProps } from "./StrategyLeaderHistoryEditor.types";

export const StrategyLeaderHistoryEditor: React.FC<StrategyLeaderHistoryEditorProps> = ({
  leader,
  factionName,
  onEdit,
}) => {
  const [isDrafting, setIsDrafting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDraft = async (): Promise<void> => {
    setIsDrafting(true);
    setErrorMessage(null);
    try {
      const story = await draftRulerBackstory({
        ruler_name: leader.name,
        faction_id: factionName,
        trait_ids: leader.trait_ids,
        ambition_ids: leader.ambition_ids,
      });
      if (story) {
        onEdit((current) => updateLeader(current, leader.id, { history: story }));
      }
    } catch {
      setErrorMessage("Could not draft history. Check connection or try again.");
    } finally {
      setIsDrafting(false);
    }
  };

  return (
    <div className="space-y-1.5 text-sm">
      <div className="flex items-center justify-between">
        <label
          htmlFor={`leader-history-${leader.id}`}
          className="font-medium text-text-primary"
        >
          Leader history & backstory
        </label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={isDrafting}
          onClick={handleDraft}
          className="text-xs text-primary"
        >
          {isDrafting ? "✦ Drafting…" : "✦ Draft with Muse"}
        </Button>
      </div>
      <textarea
        id={`leader-history-${leader.id}`}
        rows={3}
        className="w-full rounded-md border border-border-subtle bg-surface-base p-2 text-xs leading-relaxed text-content placeholder:text-content-muted focus:border-primary focus:outline-none"
        placeholder="Ancient chronicles, heroic deeds, or grievances shaping this leader…"
        value={leader.history ?? ""}
        onChange={(event) =>
          onEdit((current) =>
            updateLeader(current, leader.id, { history: event.target.value }),
          )
        }
      />
      {errorMessage && (
        <p role="alert" className="text-xs text-danger">
          {errorMessage}
        </p>
      )}
    </div>
  );
};
