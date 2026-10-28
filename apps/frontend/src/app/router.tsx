import React, { Suspense, lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { BrowseLayout } from "@/shared/components/layout/BrowseLayout";
import { AuthGuard } from "@/features/auth/components/AuthGuard/AuthGuard";
import { AlphaLockedRoute } from "@/shared/components/AlphaLockedRoute/AlphaLockedRoute";
import { RouteLoadingSpinner } from "@/shared/components/feedback/RouteLoadingSpinner";
import { LandingPage } from "@/features/landing/pages/LandingPage";

const LoginPage = lazy(() =>
  import("@/features/auth/pages/LoginPage").then((module) => ({
    default: module.LoginPage,
  })),
);
const DiscoverPage = lazy(() =>
  import("@/features/play/pages/DiscoverPage").then((module) => ({
    default: module.DiscoverPage,
  })),
);
const ScenarioFocusPage = lazy(() =>
  import("@/features/play/pages/ScenarioFocusPage").then((module) => ({
    default: module.ScenarioFocusPage,
  })),
);
const JoinPage = lazy(() =>
  import("@/features/play/pages/JoinPage").then((module) => ({
    default: module.JoinPage,
  })),
);
const ProfilePage = lazy(() =>
  import("@/features/profile/pages/ProfilePage").then((module) => ({
    default: module.ProfilePage,
  })),
);
const NotFoundPage = lazy(() =>
  import("@/features/misc/pages/NotFoundPage").then((module) => ({
    default: module.NotFoundPage,
  })),
);
const TermsPage = lazy(() =>
  import("@/features/misc/pages/TermsPage").then((module) => ({
    default: module.TermsPage,
  })),
);
const PrivacyPage = lazy(() =>
  import("@/features/misc/pages/PrivacyPage").then((module) => ({
    default: module.PrivacyPage,
  })),
);

const StudioPage = lazy(() =>
  import("@/features/studio/pages/StudioPage").then((m) => ({
    default: m.StudioPage,
  })),
);
const StudioWorkspacePage = lazy(() =>
  import("@/features/studio/pages/StudioWorkspacePage").then((m) => ({
    default: m.StudioWorkspacePage,
  })),
);
const RegionMapPage = lazy(() =>
  import("@/features/studio/pages/RegionMapPage").then((m) => ({
    default: m.RegionMapPage,
  })),
);
const CreatorStatsPage = lazy(() =>
  import("@/features/studio/pages/CreatorStatsPage").then((m) => ({
    default: m.CreatorStatsPage,
  })),
);
const ScenarioStatsPage = lazy(() =>
  import("@/features/studio/pages/ScenarioStatsPage").then((m) => ({
    default: m.ScenarioStatsPage,
  })),
);
const PlayPage = lazy(() =>
  import("@/features/play/pages/PlayPage").then((m) => ({
    default: m.PlayPage,
  })),
);
const SetupPage = lazy(() =>
  import("@/features/play/pages/SetupPage").then((m) => ({
    default: m.SetupPage,
  })),
);
const SpectatorPage = lazy(() =>
  import("@/features/play/pages/SpectatorPage").then((m) => ({
    default: m.SpectatorPage,
  })),
);
const StrategyPlayScreen = lazy(() =>
  import("@/features/play/components/PlayScreen/StrategyPlayScreen").then((m) => ({
    default: m.StrategyPlayScreen,
  })),
);

const WelcomePage = lazy(() =>
  import("@/features/onboarding/pages/WelcomePage").then((m) => ({
    default: m.WelcomePage,
  })),
);

const InvitePage = lazy(() =>
  import("@/features/studio/pages/InvitePage").then((m) => ({
    default: m.InvitePage,
  })),
);

const SettingsPage = lazy(() =>
  import("@/features/settings/pages/SettingsPage").then((m) => ({
    default: m.SettingsPage,
  })),
);

const withSuspense = (Component: React.ComponentType) => (
  <Suspense fallback={<RouteLoadingSpinner />}>
    <Component />
  </Suspense>
);

export const router = createBrowserRouter([
  {
    element: <BrowseLayout />,
    children: [
      { path: "/", element: <LandingPage /> },
      { path: "/discover", element: withSuspense(DiscoverPage) },
      {
        path: "/studio",
        element: (
          <AlphaLockedRoute>
            <AuthGuard>{withSuspense(StudioPage)}</AuthGuard>
          </AlphaLockedRoute>
        ),
      },
      {
        path: "/studio/stats",
        element: (
          <AlphaLockedRoute>
            <AuthGuard>{withSuspense(CreatorStatsPage)}</AuthGuard>
          </AlphaLockedRoute>
        ),
      },
      {
        path: "/studio/:id/stats",
        element: (
          <AlphaLockedRoute>
            <AuthGuard>{withSuspense(ScenarioStatsPage)}</AuthGuard>
          </AlphaLockedRoute>
        ),
      },
      { path: "/scenario/:id", element: withSuspense(ScenarioFocusPage) },
      {
        path: "/settings",
        element: <AuthGuard>{withSuspense(SettingsPage)}</AuthGuard>,
      },
      {
        path: "/profile",
        element: <AuthGuard>{withSuspense(ProfilePage)}</AuthGuard>,
      },
      { path: "/profile/:id", element: withSuspense(ProfilePage) },
    ],
  },
  { path: "/login", element: withSuspense(LoginPage) },
  {
    path: "/welcome",
    element: <AuthGuard>{withSuspense(WelcomePage)}</AuthGuard>,
  },
  { path: "/play", element: <Navigate to="/discover" replace /> },
  { path: "/play/strategy-preview", element: withSuspense(StrategyPlayScreen) },
  { path: "/play/:id", element: withSuspense(PlayPage) },
  { path: "/setup/:id", element: withSuspense(SetupPage) },
  {
    path: "/spectate/:id",
    element: <AlphaLockedRoute>{withSuspense(SpectatorPage)}</AlphaLockedRoute>,
  },
  {
    path: "/join",
    element: <AlphaLockedRoute>{withSuspense(JoinPage)}</AlphaLockedRoute>,
  },
  {
    path: "/studio/new",
    element: (
          <AlphaLockedRoute>
            <AuthGuard>{withSuspense(StudioWorkspacePage)}</AuthGuard>
          </AlphaLockedRoute>
        ),
  },
  {
    path: "/studio/:id/edit",
    element: (
          <AlphaLockedRoute>
            <AuthGuard>{withSuspense(StudioWorkspacePage)}</AuthGuard>
          </AlphaLockedRoute>
        ),
  },
  {
    path: "/studio/:id/region-map",
    element: (
          <AlphaLockedRoute>
            <AuthGuard>{withSuspense(RegionMapPage)}</AuthGuard>
          </AlphaLockedRoute>
        ),
  },
  {
    path: "/invite/:token",
    element: <AuthGuard>{withSuspense(InvitePage)}</AuthGuard>,
  },
  { path: "/terms", element: withSuspense(TermsPage) },
  { path: "/privacy", element: withSuspense(PrivacyPage) },
  { path: "*", element: withSuspense(NotFoundPage) },
]);
