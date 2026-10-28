import React from "react";
import type { DiscoverLayoutProps } from "./DiscoverLayout.types";

export const DiscoverLayout: React.FC<DiscoverLayoutProps> = ({
  sidebar,
  children,
}) => (
  <div className="mx-auto flex w-full max-w-[1440px] gap-8 px-4 pb-12 pt-6 md:px-8">
    {sidebar}
    <section className="flex min-w-0 flex-1 flex-col gap-6">{children}</section>
  </div>
);
