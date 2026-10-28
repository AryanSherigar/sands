import React from "react";
import { Link } from "react-router-dom";
import { STUDIO_PATH } from "@/shared/constants/navigation";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";

const PRODUCT_LINKS = [
  { to: "/discover", label: "Discover" },
  { to: STUDIO_PATH, label: "Studio" },
  { to: "/settings", label: "Settings" },
];

const LEGAL_LINKS = [
  { to: "/terms", label: "Terms" },
  { to: "/privacy", label: "Privacy" },
];

export const Footer: React.FC = () => {
  const isAlphaMode = useIsAlphaMode();
  const productLinks = isAlphaMode
    ? PRODUCT_LINKS.filter((link) => link.to !== STUDIO_PATH)
    : PRODUCT_LINKS;

  return (
    <footer className="border-t border-border-subtle bg-surface">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-6 px-6 py-8 md:flex-row md:items-center md:justify-between md:gap-4">
        <div className="flex flex-col gap-1">
          <Link
            to="/"
            className="font-mono text-lg font-semibold lowercase tracking-[0.3em] text-content"
          >
            sands
          </Link>
          <p className="max-w-xs font-mono text-xs leading-relaxed text-content-faint">
            Stories that remember. Rules the narrator obeys.
          </p>
        </div>

        <nav className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {[...productLinks, ...LEGAL_LINKS].map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="font-sans text-sm text-content-muted transition-colors hover:text-content"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="border-t border-border-subtle">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-4 font-mono text-xs text-content-faint">
          <span>© sands fiction systems. All rights reserved.</span>
          <span>engine::v1.0.4</span>
        </div>
      </div>
    </footer>
  );
};

