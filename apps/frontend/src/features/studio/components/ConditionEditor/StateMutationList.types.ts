import { StateMutation } from "@/shared/types/stateMutation.types";

export interface StateMutationListProps {
  value: StateMutation[];
  onChange: (mutations: StateMutation[]) => void;
  legend?: string;
  maxItems?: number;
}
