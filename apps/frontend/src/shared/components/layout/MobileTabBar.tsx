import React from "react";
import { useLocation } from "react-router-dom";
import {
  IconCompass,
  IconHome,
  IconPencil,
  IconUser,
} from "@tabler/icons-react";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { STUDIO_PATH } from "@/shared/constants/navigation";
import { useCreateStory } from "@/shared/hooks/useCreateStory";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { useIsKeyboardOpen } from "@/shared/hooks/useIsKeyboardOpen";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { MobileTabItem } from "./MobileTabItem";

interface TabDefinition {
  to: string;
  label: string;
  Icon: typeof IconHome;
  isExact: boolean;
  onSelect?: () => void;
}

const TABS: readonly TabDefinition[] = [
  { to: "/", label: "Home", Icon: IconHome, isExact: true },
  { to: "/discover", label: "Discover", Icon: IconCompass, isExact: false },
  { to: STUDIO_PATH, label: "Studio", Icon: IconPencil, isExact: false },
];

const PROFILE_TAB: TabDefinition = {
  to: "/profile",
  label: "Profile",
  Icon: IconUser,
  isExact: false,
};

const isTabActive = (tab: TabDefinition, pathname: string): boolean =>
  tab.isExact ? pathname === tab.to : pathname.startsWith(tab.to);

export const MobileTabBar: React.FC = () => {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const isKeyboardOpen = useIsKeyboardOpen();
  const requireSignIn = useRequireAuth("mobile-tab");
  const createStory = useCreateStory();
  const isAlphaMode = useIsAlphaMode();

  if (isKeyboardOpen) return null;

  const visibleTabs = isAlphaMode
    ? TABS.filter((tab) => tab.to !== STUDIO_PATH)
    : TABS;
  const tabs = visibleTabs.map((tab) =>
    !user && tab.to === STUDIO_PATH ? { ...tab, onSelect: createStory } : tab,
  );
  const profileTab: TabDefinition = user
    ? PROFILE_TAB
    : {
        ...PROFILE_TAB,
        label: "Sign in",
        onSelect: () => void requireSignIn(),
      };

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 flex h-16 border-t border-border-subtle bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md box-content"
    >
      {[...tabs, profileTab].map((tab) => (
        <MobileTabItem
          key={tab.label}
          label={tab.label}
          Icon={tab.Icon}
          to={tab.to}
          onSelect={tab.onSelect}
          isActive={isTabActive(tab, pathname)}
        />
      ))}
    </nav>
  );
};
