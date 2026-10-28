import React from "react";
import { TabSkeleton } from "./TabSkeleton";

export const ProfileLoadingState: React.FC = () => (
  <div className="space-y-6">
    <div className="h-60 animate-pulse rounded-md border border-border-subtle bg-surface-raised motion-reduce:animate-none" />
    <TabSkeleton />
  </div>
);
