import React from "react";
import { Link } from "react-router-dom";
import { IconArrowLeft, IconMessageCircle, IconPlayerPlay } from "@tabler/icons-react";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { ADVANCED_MODE_LABEL } from "../../constants/advancedMode";
import {
  CHAT_BUTTON_LABEL,
  PUBLISHING_NOTICE,
  STUDIO_LIST_PATH,
  UNTITLED_STORY_LABEL,
} from "../../constants/studioFrame";
import { TITLE_MAX_LENGTH } from "../../constants/guideLimits";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { EDIT_CONFLICT_MESSAGE } from "../../constants/editGuard";
import { useGuide } from "../../hooks/useGuide";
import { useOpenPlaytestTab } from "../../hooks/useOpenPlaytestTab";
import { useUnpublishedChanges } from "../../hooks/useUnpublishedChanges";
import { useSyncedTextField } from "../../hooks/useSyncedTextField";
import { getGuideStepCount } from "../../lib/guideStepsFor";
import { describeLiveStatus } from "../../lib/unpublishedChanges";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { SaveStatusIndicator } from "../SaveStatusIndicator/SaveStatusIndicator";

const reloadPage = (): void => window.location.reload();

export const StudioTopBar: React.FC = () => {
  const { scenario, saveFields, hasSaveError, retrySave } = useGuide();
  const isSaving = useStudioStore((state) => state.isSaving);
  const lastSaved = useStudioStore((state) => state.lastSaved);
  const hasEditConflict = useStudioStore((state) => state.hasEditConflict);
  const title = useSyncedTextField(
    scenario?.title ?? "",
    (next) => saveFields({ title: next }),
    TITLE_MAX_LENGTH,
  );
  const openPlaytestTab = useOpenPlaytestTab();
  const isChatOpen = useStudioTabsStore((state) => state.isChatOpen);
  const setChatOpen = useStudioTabsStore((state) => state.setChatOpen);
  const isPublishing = scenario?.status === "publishing";
  const isAdvanced = scenario?.mode === "master";
  const isLive = scenario?.status === "published";
  const unpublishedChangeCount = useUnpublishedChanges(scenario);

  const handlePublish = (): void => {
    const store = useStudioTabsStore.getState();
    store.openTab(GUIDE_TAB_ID);
    store.focusTab(GUIDE_TAB_ID);
    store.setGuideStep(getGuideStepCount(isAdvanced));
    store.setGuideView("steps");
  };

  return (
    <header className="z-40 shrink-0 border-b border-border-subtle bg-surface-sunken">
      <div className="flex items-center justify-between gap-4 px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <Link
            to={STUDIO_LIST_PATH}
            className="inline-flex shrink-0 items-center gap-1 text-meta text-content-muted transition-colors hover:text-content"
          >
            <IconArrowLeft size={14} aria-hidden="true" />
            Studio
          </Link>
          <span aria-hidden="true" className="text-content-faint">/</span>
          <input
            type="text"
            aria-label="Story name"
            placeholder={UNTITLED_STORY_LABEL}
            value={title.value}
            maxLength={TITLE_MAX_LENGTH}
            onChange={(event) => title.onChange(event.target.value)}
            className="min-w-0 flex-1 truncate rounded-sm bg-transparent px-1 py-0.5 text-body font-medium text-content placeholder:text-content-faint hover:bg-white/6 focus:bg-surface-inset focus:outline-hidden focus:ring-2 focus:ring-primary/30"
          />
          {isAdvanced && <Badge className="shrink-0">{ADVANCED_MODE_LABEL}</Badge>}
          {isLive && (
            <span className="shrink-0 text-micro text-success">
              {describeLiveStatus(unpublishedChangeCount)}
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-4">
          <span className="text-meta">
            <SaveStatusIndicator
              isSaving={isSaving}
              lastSaved={lastSaved}
              hasError={hasSaveError}
              onRetry={retrySave}
            />
          </span>
          <Button type="button" variant="secondary" size="sm" onClick={openPlaytestTab}>
            <IconPlayerPlay size={14} aria-hidden="true" />
            Playtest
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            aria-pressed={isChatOpen}
            onClick={() => setChatOpen(!isChatOpen)}
          >
            <IconMessageCircle size={14} aria-hidden="true" />
            {CHAT_BUTTON_LABEL}
          </Button>
          <Button type="button" size="sm" onClick={handlePublish}>
            {isLive ? "Publish changes" : "Publish"}
          </Button>
        </div>
      </div>
      {isPublishing && (
        <p role="status" className="border-t border-border-subtle px-4 py-2 text-meta text-info">
          {PUBLISHING_NOTICE}
        </p>
      )}
      {hasEditConflict && (
        <p
          role="alert"
          className="flex items-center gap-3 border-t border-border-subtle px-4 py-2 text-meta text-warning"
        >
          {EDIT_CONFLICT_MESSAGE}
          <Button type="button" variant="secondary" size="sm" onClick={reloadPage}>
            Reload
          </Button>
        </p>
      )}
    </header>
  );
};
