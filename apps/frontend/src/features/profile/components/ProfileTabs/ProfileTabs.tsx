import React, { useRef } from "react";
import {
  getNextTabIndex,
  getProfilePanelId,
  getProfileTabId,
} from "../../lib/profileTabs";
import type { ProfileTabsProps } from "./ProfileTabs.types";

const TAB_BASE_CLASSES =
  "relative min-h-11 shrink-0 px-4 text-sm font-medium transition duration-fast motion-reduce:transition-none focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent md:min-h-10";
const TAB_ACTIVE_CLASSES =
  "text-content after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-content";
const TAB_IDLE_CLASSES = "text-content-muted hover:text-content";

export const ProfileTabs: React.FC<ProfileTabsProps> = ({
  tabs,
  activeTab,
  onTabChange,
}) => {
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
  ) => {
    const nextIndex = getNextTabIndex(currentIndex, tabs.length, event.key);
    if (nextIndex === null) return;
    event.preventDefault();
    const nextTab = tabs[nextIndex];
    onTabChange(nextTab.id);
    tabRefs.current[nextTab.id]?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label="Profile sections"
      className="flex overflow-x-auto border-b border-border-subtle"
    >
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            ref={(node) => {
              tabRefs.current[tab.id] = node;
            }}
            type="button"
            role="tab"
            id={getProfileTabId(tab.id)}
            aria-selected={isActive}
            aria-controls={getProfilePanelId(tab.id)}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={`${TAB_BASE_CLASSES} ${isActive ? TAB_ACTIVE_CLASSES : TAB_IDLE_CLASSES}`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};
