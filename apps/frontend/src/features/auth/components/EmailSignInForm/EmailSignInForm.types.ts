export interface EmailSignInFormProps {
  onSubmit: (email: string, password: string) => Promise<boolean>;
  isPending: boolean;
  errorMessage?: string | null;
}
