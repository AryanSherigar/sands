import { useServerSyncedState } from "./useServerSyncedState";

interface SyncedValue<T> {
  value: T;
  commit: (next: T) => void;
}

export const useSyncedValue = <T>(serverValue: T, save: (next: T) => void): SyncedValue<T> => {
  const [local, setLocal] = useServerSyncedState<T>(serverValue);
  const value = local ?? serverValue;

  const commit = (next: T): void => {
    setLocal(next);
    save(next);
  };

  return { value, commit };
};
