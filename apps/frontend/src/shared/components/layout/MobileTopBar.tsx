import React, { useState } from "react";
import { IconSearch, IconX } from "@tabler/icons-react";
import { SearchField } from "./SearchField";
import { Wordmark } from "./Wordmark";

export const MobileTopBar: React.FC = () => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-border-subtle bg-surface/90 px-4 backdrop-blur-md">
      {isSearchOpen ? (
        <>
          <SearchField
            shouldAutoFocus
            className="flex-1"
            onSubmitted={() => setIsSearchOpen(false)}
          />
          <button
            type="button"
            aria-label="Close search"
            onClick={() => setIsSearchOpen(false)}
            className="flex h-10 w-10 items-center justify-center text-content-muted focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
          >
            <IconX size={20} />
          </button>
        </>
      ) : (
        <>
          <Wordmark />
          <button
            type="button"
            aria-label="Search stories"
            onClick={() => setIsSearchOpen(true)}
            className="ml-auto flex h-10 w-10 items-center justify-center text-content-muted focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
          >
            <IconSearch size={20} />
          </button>
        </>
      )}
    </header>
  );
};
