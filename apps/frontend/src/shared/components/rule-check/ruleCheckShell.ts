const OVERLAY_WRAPPER_CLASS =
  "fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-6";
const DOCKED_WRAPPER_CLASS =
  "pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center bg-linear-to-t from-black/85 via-black/40 to-transparent px-4 pb-4 pt-10";
const OVERLAY_DIALOG_CLASS = "w-full max-w-md";
const DOCKED_DIALOG_CLASS = "pointer-events-auto w-full max-w-md shadow-lg";

export const wrapperClassOf = (isDocked: boolean): string =>
  isDocked ? DOCKED_WRAPPER_CLASS : OVERLAY_WRAPPER_CLASS;

export const dialogClassOf = (isDocked: boolean): string =>
  isDocked ? DOCKED_DIALOG_CLASS : OVERLAY_DIALOG_CLASS;
