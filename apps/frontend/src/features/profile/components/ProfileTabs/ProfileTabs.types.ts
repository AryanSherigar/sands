import type {
  ProfileTabDefinition,
  ProfileTabId,
} from "../../constants/profileTabs.constants";

export interface ProfileTabsProps {
  tabs: ProfileTabDefinition[];
  activeTab: ProfileTabId;
  onTabChange: (tab: ProfileTabId) => void;
}
