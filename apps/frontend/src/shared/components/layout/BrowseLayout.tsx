import React, { Suspense } from "react";
import { Outlet, useLocation } from "react-router-dom";
import {
  DESKTOP_MEDIA_QUERY,
  SKIP_LINK_TARGET_ID,
} from "@/shared/constants/navigation";
import { useMediaQuery } from "@/shared/hooks/useMediaQuery";
import { useWindowScroll } from "@/shared/hooks/useWindowScroll";
import { cn } from "@/shared/lib/cn";
import { OnboardingBanner } from "../OnboardingBanner/OnboardingBanner";
import { RouteLoadingSpinner } from "../feedback/RouteLoadingSpinner";
import { Footer } from "./Footer";
import { MobileTabBar } from "./MobileTabBar";
import { MobileTopBar } from "./MobileTopBar";
import { TopBar } from "./TopBar";

const HOME_PATH = "/";

export const BrowseLayout: React.FC = () => {
  const { pathname } = useLocation();
  const isDesktop = useMediaQuery(DESKTOP_MEDIA_QUERY);
  const { isScrolled, isPastHero } = useWindowScroll();
  const isHome = pathname === HOME_PATH;
  const isTransparent = isHome && !isPastHero;

  return (
    <div className="min-h-screen bg-surface-sunken text-content">
      <a
        href={`#${SKIP_LINK_TARGET_ID}`}
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface-overlay focus:px-4 focus:py-2 focus:text-content"
      >
        Skip to content
      </a>
      {isHome && <OnboardingBanner />}
      {isDesktop ? (
        <TopBar isTransparent={isTransparent} isCondensed={isScrolled} />
      ) : (
        <MobileTopBar />
      )}
      <main
        id={SKIP_LINK_TARGET_ID}
        tabIndex={-1}
        className={cn(
          "focus:outline-hidden",
          !isDesktop && "pb-[calc(4rem+env(safe-area-inset-bottom))]",
        )}
      >
        <div key={pathname} className="animate-in fade-in duration-300">
          <Suspense fallback={<RouteLoadingSpinner />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
      {isHome && <Footer />}
      {!isDesktop && <MobileTabBar />}
    </div>
  );
};
