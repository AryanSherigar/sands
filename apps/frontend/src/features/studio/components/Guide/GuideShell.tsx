import React from "react";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { GuideEditorView } from "./GuideEditorView";
import { GuideStepView } from "./GuideStepView";

export const GuideShell: React.FC = () => {
  const guideView = useStudioTabsStore((state) => state.guideView);

  return (
    <div className="mx-auto w-full max-w-[640px] px-4 py-8 md:py-12">
      {guideView === "editor" ? <GuideEditorView /> : <GuideStepView />}
    </div>
  );
};
