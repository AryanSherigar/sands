import React from "react";
import { SETTINGS_SECTIONS } from "../constants/settings.constants";
import { AccountSection } from "../components/AccountSection/AccountSection";
import { DangerZoneSection } from "../components/DangerZoneSection/DangerZoneSection";
import { ContentSection } from "../components/ContentSection/ContentSection";
import { NotificationsSection } from "../components/NotificationsSection/NotificationsSection";
import { ReadingDefaultsSection } from "../components/ReadingDefaultsSection/ReadingDefaultsSection";
import { SettingsNav } from "../components/SettingsNav/SettingsNav";
import { SettingsSection } from "../components/SettingsSection/SettingsSection";

export const SettingsPage: React.FC = () => (
  <div className="mx-auto flex w-full max-w-[900px] gap-12 px-4 py-10 font-sans text-content">
    <aside className="hidden shrink-0 lg:block lg:w-48">
      <div className="sticky top-10">
        <SettingsNav sections={SETTINGS_SECTIONS} orientation="vertical" />
      </div>
    </aside>
    <div className="min-w-0 flex-1 space-y-8">
      <header className="space-y-1">
        <h1 className="font-display text-3xl font-bold tracking-tight text-content">Settings</h1>
        <p className="font-sans text-sm text-content-muted">
          Preferences for your account, reading defaults and content exposure.
        </p>
      </header>
      <div className="lg:hidden">
        <SettingsNav sections={SETTINGS_SECTIONS} />
      </div>
      <div className="space-y-12">
        <SettingsSection id="account" title="Account">
          <AccountSection />
        </SettingsSection>
        <SettingsSection id="reading" title="Reading defaults">
          <ReadingDefaultsSection />
        </SettingsSection>
        <SettingsSection id="content" title="Content preferences">
          <ContentSection />
        </SettingsSection>
        <SettingsSection id="notifications" title="Notifications">
          <NotificationsSection />
        </SettingsSection>
        <SettingsSection id="danger" title="Danger zone">
          <DangerZoneSection />
        </SettingsSection>
      </div>
    </div>
  </div>
);
