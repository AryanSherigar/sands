export interface WarCouncilLoadStateProps {
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onReturnToMap: () => void;
}

export function WarCouncilLoadState({
  isLoading,
  errorMessage,
  onRetry,
  onReturnToMap,
}: WarCouncilLoadStateProps) {
  return (
    <main className="strategy-surface fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-[#EFE4C8] text-[#221a12]">
      {isLoading ? (
        <p role="status" className="font-serif text-[18px] text-[#42474b]">
          Gathering the field reports…
        </p>
      ) : (
        <>
          <p role="alert" className="font-serif text-[18px] text-[#A8483E]">
            {errorMessage}
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onRetry}
              className="px-4 py-2 rounded-xl bg-[#2e4856] text-white text-[14px] font-semibold cursor-pointer hover:bg-[#46606E]"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={onReturnToMap}
              className="px-4 py-2 rounded-xl bg-[#fff8f4] border border-[#3A3128]/20 text-[#221a12] text-[14px] font-semibold cursor-pointer hover:bg-[#fbebde]"
            >
              Return to map
            </button>
          </div>
        </>
      )}
    </main>
  );
}
