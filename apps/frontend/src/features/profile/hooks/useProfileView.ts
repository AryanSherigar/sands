import { useEffect, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "@/features/auth/hooks/useAuth";
import type { ProfileTabId } from "../constants/profileTabs.constants";
import {
  getVisibleTabs,
  isOwnerOnlyTab,
  resolveProfileTab,
} from "../lib/profileTabs";
import { useProfilePreviewStore } from "../stores/profilePreview.store";

export const useProfileView = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const isPreviewingAsVisitor = useProfilePreviewStore(
    (state) => state.isPreviewingAsVisitor,
  );
  const setPreviewingAsVisitor = useProfilePreviewStore(
    (state) => state.setPreviewingAsVisitor,
  );

  const isOwner = Boolean(!id || (user && user.user_id === id));
  const isEffectiveOwner = isOwner && !isPreviewingAsVisitor;
  const visibleTabs = getVisibleTabs(isEffectiveOwner);
  const tabParam = searchParams.get("tab");
  const activeTab = resolveProfileTab(tabParam, visibleTabs);

  const wasPreviewingRef = useRef(false);

  useEffect(() => {
    if (isAuthLoading) return;
    const isEnteringPreview = isPreviewingAsVisitor && !wasPreviewingRef.current;
    wasPreviewingRef.current = isPreviewingAsVisitor;
    // NOTE: an owner-only ?tab= arriving while already previewing is an
    // explicit navigation (e.g. the avatar menu), so it ends the preview.
    if (isPreviewingAsVisitor && !isEnteringPreview && isOwnerOnlyTab(tabParam)) {
      setPreviewingAsVisitor(false);
      return;
    }
    if (tabParam !== null && tabParam !== activeTab) {
      setSearchParams({ tab: activeTab }, { replace: true });
    }
  }, [
    isAuthLoading,
    isPreviewingAsVisitor,
    tabParam,
    activeTab,
    setSearchParams,
    setPreviewingAsVisitor,
  ]);

  useEffect(
    () => () => setPreviewingAsVisitor(false),
    [setPreviewingAsVisitor],
  );

  const handleTabChange = (tab: ProfileTabId) => setSearchParams({ tab });

  return {
    routeUserId: id,
    currentUserId: user?.user_id,
    isOwner,
    isEffectiveOwner,
    visibleTabs,
    activeTab,
    handleTabChange,
    isAuthLoading,
    isAuthenticated,
  };
};
