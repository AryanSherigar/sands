import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { EditProfileModal } from "../components/EditProfileModal";
import { ProfileHeader } from "../components/ProfileHeader";
import { ProfileTabPanel } from "../components/ProfileTabPanel";
import { ProfileTabs } from "../components/ProfileTabs/ProfileTabs";
import { ViewingAsBar } from "../components/ViewingAsBar/ViewingAsBar";
import { ProfileLoadingState } from "../components/states/ProfileLoadingState";
import { ProfileNotFoundState } from "../components/states/ProfileNotFoundState";
import { useProfile } from "../hooks/useProfile";
import { useProfileView } from "../hooks/useProfileView";

const PAGE_CLASSES =
  "mx-auto w-full max-w-[1440px] space-y-8 px-4 pb-20 pt-4 font-sans text-content md:px-6";

export const ProfilePage: React.FC = () => {
  const view = useProfileView();
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const isProfileEnabled =
    Boolean(view.routeUserId) || (!view.isAuthLoading && view.isAuthenticated);
  const { data: profile, isLoading, isError } = useProfile(
    view.routeUserId || "me",
    { enabled: isProfileEnabled, currentUserId: view.currentUserId },
  );

  if (!view.routeUserId && !view.isAuthLoading && !view.isAuthenticated) {
    return <Navigate to="/login?redirect=/profile" replace />;
  }
  if (view.isAuthLoading || (isProfileEnabled && isLoading)) {
    return (
      <div className={PAGE_CLASSES}>
        <ProfileLoadingState />
      </div>
    );
  }
  if (isError || !profile) return <ProfileNotFoundState />;

  return (
    <div className={PAGE_CLASSES}>
      {view.isOwner && <ViewingAsBar />}
      <ProfileHeader
        profile={profile}
        isOwner={view.isEffectiveOwner}
        onEditClick={() => setIsEditModalOpen(true)}
      />
      <ProfileTabs
        tabs={view.visibleTabs}
        activeTab={view.activeTab}
        onTabChange={view.handleTabChange}
      />
      <ProfileTabPanel
        activeTab={view.activeTab}
        userId={profile.user_id}
        isOwner={view.isEffectiveOwner}
        isViewerOwner={view.isOwner}
      />
      {view.isEffectiveOwner && isEditModalOpen && (
        <EditProfileModal
          profile={profile}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
        />
      )}
    </div>
  );
};
