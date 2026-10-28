import React from "react";
import { OverflowMenu } from "@/shared/components/ui/OverflowMenu";
import type { AdvancedCardProps } from "./Advanced.types";

export const AdvancedCard: React.FC<AdvancedCardProps> = ({
  ariaLabel,
  badge,
  menuLabel,
  menuItems,
  leading,
  cardRef,
  style,
  children,
}) => (
  <article
    ref={cardRef}
    style={style}
    aria-label={ariaLabel}
    className="space-y-4 rounded-lg border border-border-subtle bg-surface-raised p-4"
  >
    <header className="flex items-center gap-2">
      {leading}
      <span className="rounded-sm border border-border-strong px-2 py-0.5 text-micro text-content-muted">
        {badge}
      </span>
      <div className="ml-auto">
        <OverflowMenu label={menuLabel} items={menuItems} />
      </div>
    </header>
    {children}
  </article>
);
