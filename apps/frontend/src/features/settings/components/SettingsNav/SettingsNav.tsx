import React from "react";
import { Link } from "react-router-dom";
import { IconArrowRight, IconCheck, IconAlertTriangle } from "@tabler/icons-react";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type { SettingsNavProps } from "./SettingsNav.types";

const SAVED_LOCALLY_LABEL = "Saved locally";
const STORAGE_ERROR_LABEL = "Couldn't save locally";

export const SettingsNav: React.FC<SettingsNavProps> = ({
  sections,
  orientation = "horizontal",
}) => {
  const hasStorageError = useReaderPreferencesStore(
    (state) => state.hasStorageError,
  );
  const persistAll = useReaderPreferencesStore((state) => state.persistAll);
  const isVertical = orientation === "vertical";

  return (
    <nav
      aria-label="Settings sections"
      className={
        isVertical
          ? "flex flex-col gap-1"
          : "flex flex-wrap items-center gap-2 border-b border-border-subtle pb-4"
      }
    >
      <div className={isVertical ? "flex flex-col gap-1" : "flex flex-wrap items-center gap-1"}>
        {sections.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className={`inline-flex min-h-8 items-center rounded-md px-2.5 py-1 font-sans text-xs font-medium text-content-muted transition-colors duration-100 hover:bg-surface-raised hover:text-content${isVertical ? " w-full" : ""}`}
          >
            {section.label}
          </a>
        ))}
      </div>
      {!isVertical && (
        <>
          <div
            role="status"
            aria-live="polite"
            className="ml-auto flex items-center gap-2 rounded-md border border-border-subtle bg-surface-raised px-2.5 py-1 font-sans text-xs"
          >
            {hasStorageError ? (
              <>
                <IconAlertTriangle size={14} stroke={1.5} aria-hidden="true" className="text-danger" />
                <span className="text-danger">{STORAGE_ERROR_LABEL}</span>
                <button
                  type="button"
                  onClick={persistAll}
                  className="ml-auto font-semibold underline underline-offset-2 text-content"
                >
                  Retry
                </button>
              </>
            ) : (
              <>
                <IconCheck size={14} stroke={1.5} aria-hidden="true" className="text-success" />
                <span className="text-content-muted">{SAVED_LOCALLY_LABEL}</span>
              </>
            )}
          </div>
          <Link
            to="/profile"
            className="inline-flex items-center gap-1 px-2 font-sans text-xs text-content-muted hover:text-content"
          >
            View public profile
            <IconArrowRight size={14} stroke={1.5} aria-hidden="true" />
          </Link>
        </>
      )}
    </nav>
  );
};
