export type HorrorExperience = "none" | "some" | "a_lot";
export type UsualDevice = "phone" | "tablet" | "laptop_or_desktop";

interface IntakeAnswers {
  horror_experience: HorrorExperience;
  usual_device: UsualDevice;
}

export interface PostRunAnswers {
  rating: number;
  scariness: number;
  confusing?: string;
  would_have_stopped?: string;
}

export type AlphaSurveyRequest =
  | { kind: "intake"; answers: IntakeAnswers }
  | { kind: "post_run"; playthrough_id: string; answers: PostRunAnswers };

export interface AlphaSurveyAccepted {
  kind: "intake" | "post_run";
}
