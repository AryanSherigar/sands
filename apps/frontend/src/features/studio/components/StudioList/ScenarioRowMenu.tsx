import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  IconArchive,
  IconCopy,
  IconDots,
  IconExternalLink,
  IconTrash,
} from "@tabler/icons-react";
import { useToast } from "@/shared/hooks/useToast";
import { useArchiveScenario } from "../../hooks/useArchiveScenario";
import { useDuplicateScenario } from "../../hooks/useDuplicateScenario";
import { isLiveStatus } from "../../utils/scenarioRowStatus";
import type { ScenarioRowMenuProps } from "./StudioList.types";

const ITEM_CLASSES =
  "flex w-full items-center gap-2.5 px-4 py-2 text-left transition-colors hover:bg-surface-raised hover:text-content focus-visible:bg-surface-raised focus-visible:outline-hidden";
const DELETE_HIDDEN_STATUSES = ["publishing", "archived"];

export const ScenarioRowMenu: React.FC<ScenarioRowMenuProps> = ({
  scenario,
  status,
  onDelete,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const navigate = useNavigate();
  const showToast = useToast();
  const { duplicate, isDuplicating } = useDuplicateScenario(scenario.scenario_id);
  const { archive, isArchiving } = useArchiveScenario(scenario.scenario_id);
  const isGuideDraft = status === "draft" && scenario.mode === "newbie";

  useEffect(() => {
    if (!isOpen) return undefined;
    const handlePointerDown = (event: MouseEvent): void => {
      if (!rootRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [isOpen]);

  const handleKeyDown = (event: React.KeyboardEvent): void => {
    if (event.key !== "Escape") return;
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const handleDuplicate = (): void => {
    setIsOpen(false);
    duplicate(undefined, {
      onSuccess: (copy) =>
        showToast("Copy created", "success", {
          label: "Open",
          onClick: () => navigate(`/studio/${copy.scenario_id}/edit`),
        }),
      onError: () => showToast("Couldn't duplicate the scenario.", "error"),
    });
  };

  const handleArchive = (): void => {
    setIsOpen(false);
    archive(undefined, {
      onSuccess: () => showToast("Draft archived", "success"),
      onError: () => showToast("Couldn't archive the draft.", "error"),
    });
  };

  const handleDelete = (): void => {
    setIsOpen(false);
    onDelete(scenario);
  };

  return (
    <div className="relative" ref={rootRef} onKeyDown={handleKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={`More actions for ${scenario.title || "untitled scenario"}`}
        onClick={() => setIsOpen((previous) => !previous)}
        className="flex h-9 w-9 items-center justify-center rounded-md border border-border-subtle bg-surface-raised text-content-muted transition-colors hover:bg-surface-overlay hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        <IconDots size={20} aria-hidden="true" />
      </button>
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-2 w-52 overflow-hidden rounded-lg border border-border-subtle bg-surface-overlay py-1 font-sans text-sm text-content-muted shadow-elevated"
        >
          {isLiveStatus(status) && (
            <Link
              to={`/scenario/${scenario.scenario_id}`}
              role="menuitem"
              className={ITEM_CLASSES}
            >
              <IconExternalLink size={16} aria-hidden="true" />
              View public page
            </Link>
          )}
          <button
            type="button"
            role="menuitem"
            disabled={isDuplicating}
            onClick={handleDuplicate}
            className={ITEM_CLASSES}
          >
            <IconCopy size={16} aria-hidden="true" />
            Duplicate
          </button>
          {isGuideDraft && (
            <button
              type="button"
              role="menuitem"
              disabled={isArchiving}
              onClick={handleArchive}
              className={ITEM_CLASSES}
            >
              <IconArchive size={16} aria-hidden="true" />
              Archive
            </button>
          )}
          {!DELETE_HIDDEN_STATUSES.includes(scenario.status) && (
            <button
              type="button"
              role="menuitem"
              onClick={handleDelete}
              className={`${ITEM_CLASSES} text-danger hover:bg-danger/10`}
            >
              <IconTrash size={16} aria-hidden="true" />
              {isGuideDraft ? "Delete draft" : "Delete"}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
