import { useSyncedValue } from "./useSyncedValue";

export const useSyncedTextField = (
  serverValue: string,
  save: (next: string) => void,
  maxLength?: number,
) => {
  const { value, commit } = useSyncedValue(serverValue, save);

  const onChange = (next: string): void =>
    commit(maxLength === undefined ? next : next.slice(0, maxLength));

  return { value, onChange };
};
