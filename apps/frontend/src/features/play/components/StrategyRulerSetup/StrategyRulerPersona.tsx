import React, { useState, useMemo } from "react";
import { IconArrowRight, IconRestore } from "@tabler/icons-react";
import { SovereignIdentityCard } from "./SovereignIdentityCard";
import { ChronicleBackstoryField } from "./ChronicleBackstoryField";
import { SovereignTraitsModule } from "./SovereignTraitsModule";
import { SovereignAmbitionsModule } from "./SovereignAmbitionsModule";
import { TraitSelectionDrawer } from "./TraitSelectionDrawer";
import { AmbitionSelectionDrawer } from "./AmbitionSelectionDrawer";
import { BUILTIN_STRATEGY_TRAITS } from "./builtinTraits";
import { BUILTIN_STRATEGY_AMBITIONS } from "./builtinAmbitions";
import type { StrategyTrait, StrategyAmbition } from "./StrategyRulerSetup.types";
import type { StrategyRulerPersonaProps } from "./StrategyRulerPersona.types";

function PersonaHeader() {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-2xl font-bold text-[#221a12]">
          Forge Sovereign Persona
        </h2>
        <span className="text-xs text-[#785a00] font-semibold tracking-wide bg-[#ffdf9d]/50 px-2 py-0.5 rounded">
          Character Sheet
        </span>
      </div>
      <p className="text-sm text-[#42474b] italic font-serif">
        Shape the lineage, virtues, and mortal aspirations of your coronation portrait.
      </p>
    </div>
  );
}

function PersonaActions({
  onResetDefault,
  onBeginReign,
  isSubmitting,
}: {
  onResetDefault?: () => void;
  onBeginReign?: () => void;
  isSubmitting?: boolean;
}) {
  if (!onBeginReign && !onResetDefault) return null;

  return (
    <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
      {onResetDefault && (
        <button
          type="button"
          onClick={onResetDefault}
          className="order-2 sm:order-1 text-sm text-[#42474b] hover:text-[#221a12] flex items-center gap-1.5 transition-colors"
        >
          <IconRestore size={16} />
          <span>Restore Default Ruler</span>
        </button>
      )}
      {onBeginReign && (
        <button
          type="button"
          onClick={onBeginReign}
          disabled={isSubmitting}
          className="order-1 sm:order-2 w-full sm:w-auto px-6 py-2.5 rounded-lg bg-[#785a00] hover:bg-[#967000] text-white transition-all shadow-md hover:shadow-lg active:translate-y-px flex items-center justify-center gap-2 group font-serif text-base font-semibold disabled:opacity-50"
        >
          <span>{isSubmitting ? "Inscribing Campaign..." : "Begin Reign Anno 1042"}</span>
          <IconArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </button>
      )}
    </div>
  );
}

function resolveTraits(traitIds: string[], availableTraits: StrategyTrait[]): StrategyTrait[] {
  const map = new Map<string, StrategyTrait>();
  BUILTIN_STRATEGY_TRAITS.forEach((t) => map.set(t.id, t));
  availableTraits.forEach((t) => map.set(t.id, t));
  return traitIds.map(
    (id) =>
      map.get(id) || {
        id,
        name: id.replace(/_/g, " "),
        description: "Sovereign virtue",
        effects: [],
      }
  );
}

function resolveAmbitions(ambitionIds: string[], availableAmbitions: StrategyAmbition[]): StrategyAmbition[] {
  const map = new Map<string, StrategyAmbition>();
  BUILTIN_STRATEGY_AMBITIONS.forEach((a) => map.set(a.id, a));
  availableAmbitions.forEach((a) => map.set(a.id, a));
  return ambitionIds.map(
    (id) =>
      map.get(id) || {
        id,
        name: id.replace(/_/g, " "),
        description: "Coronation ambition",
        progress: 0,
      }
  );
}

export const StrategyRulerPersona: React.FC<StrategyRulerPersonaProps> = ({
  ruler,
  onUpdateRuler,
  onRedraftBackstory,
  isRedrafting,
  availableTraits = [],
  availableAmbitions = [],
  onResetDefault,
  onBeginReign,
  isSubmitting = false,
}) => {
  const [isTraitDrawerOpen, setIsTraitDrawerOpen] = useState(false);
  const [isAmbitionDrawerOpen, setIsAmbitionDrawerOpen] = useState(false);

  const activeTraits = useMemo(
    () => resolveTraits(ruler.traitIds, availableTraits),
    [ruler.traitIds, availableTraits]
  );

  const activeAmbitions = useMemo(
    () => resolveAmbitions(ruler.ambitionIds, availableAmbitions),
    [ruler.ambitionIds, availableAmbitions]
  );

  return (
    <section className="flex flex-col gap-4">
      <PersonaHeader />
      <SovereignIdentityCard
        name={ruler.name}
        epithet={ruler.epithet}
        portraitUrl={ruler.portraitUrl}
        dynastyName={ruler.dynastyName}
        houseMotto={ruler.houseMotto}
        onChangeName={(name) => onUpdateRuler({ name })}
        onChangeEpithet={(epithet) => onUpdateRuler({ epithet })}
      />
      <ChronicleBackstoryField
        backstory={ruler.backstory}
        isRedrafting={isRedrafting}
        onChangeBackstory={(backstory) => onUpdateRuler({ backstory })}
        onRedraft={onRedraftBackstory}
      />
      <SovereignTraitsModule
        activeTraits={activeTraits}
        onOpenDrawer={() => setIsTraitDrawerOpen(true)}
      />
      <SovereignAmbitionsModule
        activeAmbitions={activeAmbitions}
        onOpenDrawer={() => setIsAmbitionDrawerOpen(true)}
      />
      <PersonaActions
        onResetDefault={onResetDefault}
        onBeginReign={onBeginReign}
        isSubmitting={isSubmitting}
      />
      <TraitSelectionDrawer
        isOpen={isTraitDrawerOpen}
        selectedTraitIds={ruler.traitIds}
        availableTraits={availableTraits}
        onSelectTraits={(traitIds) => onUpdateRuler({ traitIds })}
        onClose={() => setIsTraitDrawerOpen(false)}
      />
      <AmbitionSelectionDrawer
        isOpen={isAmbitionDrawerOpen}
        selectedAmbitionIds={ruler.ambitionIds}
        availableAmbitions={availableAmbitions}
        onSelectAmbitions={(ambitionIds) => onUpdateRuler({ ambitionIds })}
        onClose={() => setIsAmbitionDrawerOpen(false)}
      />
    </section>
  );
};
