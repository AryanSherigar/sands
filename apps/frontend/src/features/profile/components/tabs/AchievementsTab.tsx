import React from "react";
import { useProfileAchievements } from "../../hooks/useProfileAchievements";
import { groupByFamily, visibleAchievements } from "../../lib/achievements";
import { AchievementFamilySection } from "../achievements/AchievementFamilySection/AchievementFamilySection";
import { TabEmptyState } from "../states/TabEmptyState";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";
import type { AchievementsTabProps } from "./AchievementsTab.types";

export const AchievementsTab: React.FC<AchievementsTabProps> = ({
  userId,
  isOwnerData,
  isProgressVisible,
}) => {
  const { data, isLoading, isError } = useProfileAchievements(
    userId,
    isOwnerData,
  );

  if (isLoading) return <TabSkeleton />;
  if (isError || !data) {
    return <TabErrorState message="Couldn't load achievements." />;
  }

  const groups = groupByFamily(visibleAchievements(data, isProgressVisible));
  if (groups.length === 0) {
    return <TabEmptyState message="No achievements earned yet" />;
  }

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <AchievementFamilySection
          key={group.family}
          family={group.family}
          items={group.items}
        />
      ))}
    </div>
  );
};
