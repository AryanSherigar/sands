import React from "react";
import { IconSparkles } from "@tabler/icons-react";
import { SidebarButton } from "@/shared/components/layout/SidebarButton";
import {
  NEW_FEATURES_LABEL,
  NO_NEW_FEATURES_MESSAGE,
  type NewFeature,
} from "../../constants/newFeatures";
import { useNewFeatures } from "../../hooks/useNewFeatures";
import { buildFeatureTabId } from "../../lib/studioTabs";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { YourStoryGroup } from "./YourStoryGroup";

const FeatureRow: React.FC<{ feature: NewFeature }> = ({ feature }) => {
  const tabId = buildFeatureTabId(feature.id);
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const openTab = useStudioTabsStore((state) => state.openTab);

  return (
    <SidebarButton
      icon={<IconSparkles size={16} aria-hidden="true" />}
      label={feature.name}
      isActive={activeTabId === tabId}
      onClick={() => openTab(tabId)}
    />
  );
};

export const NewFeaturesSection: React.FC = () => {
  const { hasScenario, eligible, unseen, seen, unseenCount } = useNewFeatures();
  if (!hasScenario) return null;

  return (
    <YourStoryGroup label={NEW_FEATURES_LABEL} count={unseenCount}>
      {eligible.length === 0 && (
        <p className="px-2 text-micro text-content-faint">{NO_NEW_FEATURES_MESSAGE}</p>
      )}
      {unseen.map((feature) => (
        <FeatureRow key={feature.id} feature={feature} />
      ))}
      {seen.length > 0 && (
        <details className="px-1">
          <summary className="cursor-pointer px-1 py-1 text-micro text-content-faint">
            Seen ({seen.length})
          </summary>
          <div className="space-y-0.5">
            {seen.map((feature) => (
              <FeatureRow key={feature.id} feature={feature} />
            ))}
          </div>
        </details>
      )}
    </YourStoryGroup>
  );
};
