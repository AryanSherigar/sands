import type { ProfileTabId } from "../constants/profileTabs.constants";

export interface ProfileTabPanelProps {
  activeTab: ProfileTabId;
  userId: string;
  isOwner: boolean;
  isViewerOwner: boolean;
}
