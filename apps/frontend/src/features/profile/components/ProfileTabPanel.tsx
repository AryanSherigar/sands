import React from "react";
import { getProfilePanelId, getProfileTabId } from "../lib/profileTabs";
import { BookmarksTab } from "./tabs/BookmarksTab";
import { AchievementsTab } from "./tabs/AchievementsTab";
import { CampaignsTab } from "./tabs/CampaignsTab";
import { CreationsTab } from "./tabs/CreationsTab";
import { EndingsTab } from "./tabs/EndingsTab";
import { OverviewTab } from "./tabs/OverviewTab";
import { ReviewsTab } from "./tabs/ReviewsTab";
import type { ProfileTabPanelProps } from "./ProfileTabPanel.types";

export const ProfileTabPanel: React.FC<ProfileTabPanelProps> = ({
  activeTab,
  userId,
  isOwner,
  isViewerOwner,
}) => (
  <div
    role="tabpanel"
    id={getProfilePanelId(activeTab)}
    aria-labelledby={getProfileTabId(activeTab)}
    tabIndex={0}
    className="transition-opacity duration-fast motion-reduce:transition-none"
  >
    {isOwner && activeTab === "overview" && <OverviewTab />}
    {activeTab === "creations" && (
      <CreationsTab userId={userId} isOwner={isOwner} />
    )}
    {isOwner && activeTab === "campaigns" && <CampaignsTab />}
    {isOwner && activeTab === "endings" && <EndingsTab />}
    {activeTab === "achievements" && (
      <AchievementsTab
        userId={userId}
        isOwnerData={isViewerOwner}
        isProgressVisible={isOwner}
      />
    )}
    {isOwner && activeTab === "bookmarks" && <BookmarksTab />}
    {activeTab === "reviews" && <ReviewsTab userId={userId} />}
  </div>
);
