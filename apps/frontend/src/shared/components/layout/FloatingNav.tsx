import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { IconSearch } from "@tabler/icons-react";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { usePageScrollCompact } from "@/shared/hooks/usePageScrollCompact";
import { cn } from "@/shared/lib/cn";
import { UserDropdown } from "./UserDropdown";

const LINKS = [
  { to: "/", label: "Home", exact: true },
  { to: "/discover", label: "Discover", exact: false },
  { to: "/studio", label: "Studio", exact: false },
];

const SPRING = { type: "spring", stiffness: 320, damping: 34 } as const;

export const FloatingNav: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isCompact = usePageScrollCompact();
  const [query, setQuery] = useState("");

  const isActive = (to: string, exact: boolean): boolean =>
    exact ? location.pathname === to : location.pathname.startsWith(to);

  const handleSearchSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    const trimmed = query.trim();
    void navigate(
      trimmed ? `/discover?q=${encodeURIComponent(trimmed)}` : "/discover",
    );
  };

  return (
    <div className="pointer-events-none absolute inset-x-0 top-2.5 z-30 flex justify-center px-3">
      <motion.nav className="pointer-events-auto flex items-center gap-1 rounded-full border border-border-strong bg-surface/85 p-1.5 pl-4 shadow-elevated backdrop-blur-md">
        <Link
          to="/"
          className="mr-1 shrink-0 font-mono text-sm font-semibold lowercase tracking-[0.25em] text-content transition-colors hover:text-content-muted"
        >
          sands
        </Link>

        {LINKS.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className={cn(
              "shrink-0 rounded-full px-3 py-1.5 font-sans text-sm transition-colors",
              isActive(link.to, link.exact)
                ? "bg-surface-overlay text-content"
                : "text-content-muted hover:text-content",
            )}
          >
            {link.label}
          </Link>
        ))}

        <AnimatePresence initial={false} mode="wait">
          {isCompact ? (
            <motion.button
              key="search-icon"
              type="button"
              onClick={() => navigate("/discover")}
              aria-label="Search scenarios"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={SPRING}
              className="ml-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border-strong bg-surface-inset text-content transition-colors hover:text-content-muted"
            >
              <IconSearch size={16} stroke={1.5} />
            </motion.button>
          ) : (
            <motion.form
              key="search-input"
              onSubmit={handleSearchSubmit}
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              transition={SPRING}
              className="relative ml-1 flex items-center overflow-hidden"
            >
              <IconSearch
                size={16}
                stroke={1.5}
                className="pointer-events-none absolute left-2.5 text-content-faint"
              />
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search"
                aria-label="Search scenarios"
                className="w-40 rounded-full border border-border-strong bg-surface-inset py-1.5 pl-8 pr-3 font-sans text-sm text-content placeholder:text-content-faint transition duration-base focus-visible:border-primary focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary/20 lg:w-52"
              />
            </motion.form>
          )}
        </AnimatePresence>

        <span className="mx-1 h-4 w-px shrink-0 bg-border-strong" />

        {user ? (
          <UserDropdown user={user} onLogout={logout} />
        ) : (
          <Link
            to="/login"
            className="shrink-0 rounded-full bg-primary px-4 py-1.5 font-sans text-sm font-semibold text-primary-contrast transition duration-base hover:bg-primary/90 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            Sign in
          </Link>
        )}
      </motion.nav>
    </div>
  );
};
