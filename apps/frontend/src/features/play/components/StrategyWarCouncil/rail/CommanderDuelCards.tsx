export interface CommanderProfile {
  name: string;
  portraitUrl?: string;
  mood?: string;
  traits?: string[];
}

export interface CommanderDuelCardsProps {
  playerCommander: CommanderProfile | null;
  enemyCommander: CommanderProfile | null;
}

interface CommanderCardProps {
  commander: CommanderProfile;
  fallbackIcon: string;
  accentClass: string;
  portraitBackgroundClass: string;
  cardClass: string;
}

function CommanderCard({
  commander,
  fallbackIcon,
  accentClass,
  portraitBackgroundClass,
  cardClass,
}: CommanderCardProps) {
  return (
    <div className={`flex items-center gap-2.5 p-2 rounded-xl shadow-sm border border-[#3A3128]/10 transition-colors ${cardClass}`}>
      <div className={`relative w-11 h-11 rounded-full overflow-hidden shrink-0 shadow-inner flex items-center justify-center text-white ${portraitBackgroundClass}`}>
        {commander.portraitUrl ? (
          <img className="w-full h-full object-cover" src={commander.portraitUrl} alt={commander.name} />
        ) : (
          <span className="material-symbols-outlined text-[24px]">{fallbackIcon}</span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="font-serif text-[15px] truncate text-[#221a12] font-semibold">{commander.name}</span>
          {commander.mood ? (
            <span className={`text-[11px] uppercase font-semibold ${accentClass}`}>{commander.mood}</span>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-1 mt-0.5">
          {(commander.traits ?? []).map((trait) => (
            <span key={trait} className="px-1.5 py-0.5 rounded bg-[#fbebde] text-[11px] text-[#2e4856] font-medium">
              {trait}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function CommanderDuelCards({ playerCommander, enemyCommander }: CommanderDuelCardsProps) {
  if (!playerCommander && !enemyCommander) return null;

  return (
    <div className="flex flex-col gap-2">
      {playerCommander ? (
        <CommanderCard
          commander={playerCommander}
          fallbackIcon="person"
          accentClass="text-[#5E8A5A]"
          portraitBackgroundClass="bg-[#46606E]"
          cardClass="bg-[#F7F0DC]/85 hover:border-[#D2A94A]/40"
        />
      ) : null}
      {enemyCommander ? (
        <CommanderCard
          commander={enemyCommander}
          fallbackIcon="swords"
          accentClass="text-[#7c2820]"
          portraitBackgroundClass="bg-[#9b3f35]"
          cardClass="bg-[#F7F0DC]/70 hover:border-[#7c2820]/40"
        />
      ) : null}
    </div>
  );
}
