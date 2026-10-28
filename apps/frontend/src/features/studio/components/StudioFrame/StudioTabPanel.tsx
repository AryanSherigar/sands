import React from "react";
import { getExtraByFeatureId } from "../../lib/extras";
import { getFeatureById } from "../../lib/newFeatures";
import { parseTabId } from "../../lib/studioTabs";
import { NewFeatureTab } from "../NewFeatures/NewFeatureTab";
import { PlaytestTab } from "../PlaytestTab/PlaytestTab";
import { GuideShell } from "../Guide/GuideShell";
import { CardTabPanel } from "./CardTabPanel";
import { ExtraEditorPanel } from "./ExtraEditorPanel";
import type { StudioTabPanelProps } from "./StudioFrame.types";
import { TabPlaceholder } from "./TabPlaceholder";

export const StudioTabPanel: React.FC<StudioTabPanelProps> = ({ tabId }) => {
  const target = parseTabId(tabId);
  if (!target) return null;
  if (target.kind === "guide") return <GuideShell />;
  if (target.kind === "card" && target.targetId) {
    return <CardTabPanel entityId={target.targetId} />;
  }
  if (target.kind === "playtest") return <PlaytestTab />;
  const extra = target.targetId ? getExtraByFeatureId(target.targetId) : null;
  if (extra) return <ExtraEditorPanel extra={extra} />;
  const feature = target.targetId ? getFeatureById(target.targetId) : null;
  if (feature) return <NewFeatureTab feature={feature} />;
  return <TabPlaceholder label="This feature page" />;
};
