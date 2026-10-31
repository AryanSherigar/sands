from strategy_contracts.conditions import (
    SUBJECT_PLACEHOLDER,
    AllOf,
    AnyOf,
    Comparison,
    Condition,
    ConditionMetric,
    ConditionOperator,
    ConditionScope,
    metric_scope,
)
from strategy_contracts.events import (
    EffectKind,
    EffectSpec,
    EventChoice,
    EventDefinition,
    SeverityTier,
)

GRIEVANCE_UNREST_TIERS = (40, 60, 80)
GRIEVANCE_OPINION_FLOOR = -20
DEFIANCE_OPINION_TIERS = (-30, -50, -70)
DEFIANCE_LOW_TREASURY = 50
DEFIANCE_HIGH_EXHAUSTION = 60
MUTINY_MORALE_CEILINGS = (60, 40)
MUTINY_UNPAID_TURNS = (1, 2, 3)
TURMOIL_UNREST_THRESHOLD = 60
TURMOIL_REGION_COUNTS = (2, 3, 4)
CHEAP_FIX_COST = 1
COSTLY_FIX_COST = 2
CONCESSION_SCAR = 5
HARVEST_MONTHS = (8, 10)
PLAGUE_MONTHS = (6, 9)
BAD_HARVEST_CHANCE = 40
PLAGUE_CHANCE = 15
HUNGER_UNREST_THRESHOLDS = (40, 60)
FAMINE_STABILITY_CEILING = 40
PLAGUE_EXHAUSTION_TIERS = (30, 50, 70)
DISASTER_SCAR = 10
CRACKDOWN_SCAR = 25


def _compare(
    metric: ConditionMetric,
    operator: ConditionOperator,
    value: int,
    *,
    threshold: int | None = None,
) -> Comparison:
    scope_is_subject = metric_scope(metric) is not ConditionScope.FACTION
    return Comparison(
        metric=metric,
        operator=operator,
        value=value,
        threshold=threshold,
        subject_id=SUBJECT_PLACEHOLDER if scope_is_subject else None,
    )


def _effect(kind: EffectKind, amount: int, *, on_subject: bool = True) -> EffectSpec:
    return EffectSpec(
        kind=kind, amount=amount, target_id=SUBJECT_PLACEHOLDER if on_subject else None
    )


def _tier(level: int, trigger: Condition) -> SeverityTier:
    return SeverityTier(level=level, trigger=trigger)


def _tax_grievance() -> EventDefinition:
    unrest = ConditionMetric.REGION_UNREST
    opinion = ConditionMetric.GOVERNOR_OPINION
    first, second, third = GRIEVANCE_UNREST_TIERS
    return EventDefinition(
        id="tax_grievance",
        name="Tax grievance",
        subject_kind=ConditionScope.REGION,
        cause_key="tax_grievance",
        cause_metrics=[unrest, opinion],
        tiers=[
            _tier(1, _compare(unrest, ConditionOperator.GTE, first)),
            _tier(
                2,
                AllOf(
                    conditions=[
                        _compare(unrest, ConditionOperator.GTE, second),
                        _compare(
                            opinion, ConditionOperator.LTE, GRIEVANCE_OPINION_FLOOR
                        ),
                    ]
                ),
            ),
            _tier(3, _compare(unrest, ConditionOperator.GTE, third)),
        ],
        choices=[
            EventChoice(
                id="ease_taxes",
                label_hint="Lighten the levy in this region",
                order_cost=CHEAP_FIX_COST,
                scar_amount=CONCESSION_SCAR,
                effects=[
                    _effect(EffectKind.REGION_UNREST, -10),
                    _effect(EffectKind.GOLD, -20, on_subject=False),
                ],
            ),
            EventChoice(
                id="garrison_crackdown",
                label_hint="Send troops to break the protest",
                order_cost=COSTLY_FIX_COST,
                scar_amount=CRACKDOWN_SCAR,
                effects=[
                    _effect(EffectKind.REGION_UNREST, -15),
                    _effect(EffectKind.GOVERNOR_OPINION, -10),
                    _effect(EffectKind.MANPOWER, -10),
                ],
            ),
        ],
        neglect_effects=[
            _effect(EffectKind.REGION_UNREST, 10),
            _effect(EffectKind.GOVERNOR_OPINION, -10),
        ],
    )


def _noble_defiance() -> EventDefinition:
    opinion = ConditionMetric.GOVERNOR_OPINION
    first, second, third = DEFIANCE_OPINION_TIERS
    strained = AnyOf(
        conditions=[
            Comparison(
                metric=ConditionMetric.TREASURY,
                operator=ConditionOperator.LTE,
                value=DEFIANCE_LOW_TREASURY,
            ),
            Comparison(
                metric=ConditionMetric.WAR_EXHAUSTION,
                operator=ConditionOperator.GTE,
                value=DEFIANCE_HIGH_EXHAUSTION,
            ),
        ]
    )
    return EventDefinition(
        id="noble_defiance",
        name="Noble defiance",
        subject_kind=ConditionScope.GOVERNOR,
        cause_key="noble_defiance",
        cause_metrics=[opinion, ConditionMetric.TREASURY],
        tiers=[
            _tier(1, _compare(opinion, ConditionOperator.LTE, first)),
            _tier(
                2,
                AllOf(
                    conditions=[
                        _compare(opinion, ConditionOperator.LTE, second),
                        strained,
                    ]
                ),
            ),
            _tier(3, _compare(opinion, ConditionOperator.LTE, third)),
        ],
        choices=[
            EventChoice(
                id="grant_concession",
                label_hint="Grant the lord a concession",
                order_cost=CHEAP_FIX_COST,
                scar_amount=CONCESSION_SCAR,
                effects=[
                    _effect(EffectKind.GOLD, -30, on_subject=False),
                    _effect(EffectKind.GOVERNOR_OPINION, 15),
                ],
            ),
            EventChoice(
                id="summon_to_court",
                label_hint="Summon the lord to answer to the crown",
                order_cost=COSTLY_FIX_COST,
                scar_amount=CRACKDOWN_SCAR,
                effects=[
                    _effect(EffectKind.GOVERNOR_OPINION, -10),
                    _effect(EffectKind.STABILITY, 2, on_subject=False),
                ],
            ),
        ],
        neglect_effects=[
            _effect(EffectKind.REGION_UNREST, 10),
            _effect(EffectKind.STABILITY, -5, on_subject=False),
        ],
    )


def _unpaid_mutiny() -> EventDefinition:
    unpaid = ConditionMetric.ARMY_UNPAID_TURNS
    morale = ConditionMetric.ARMY_MORALE
    first_turns, second_turns, third_turns = MUTINY_UNPAID_TURNS
    first_morale, second_morale = MUTINY_MORALE_CEILINGS
    return EventDefinition(
        id="unpaid_mutiny",
        name="Unpaid troops",
        subject_kind=ConditionScope.ARMY,
        cause_key="unpaid_mutiny",
        cause_metrics=[unpaid, morale],
        tiers=[
            _tier(
                1,
                AllOf(
                    conditions=[
                        _compare(unpaid, ConditionOperator.GTE, first_turns),
                        _compare(morale, ConditionOperator.LTE, first_morale),
                    ]
                ),
            ),
            _tier(
                2,
                AllOf(
                    conditions=[
                        _compare(unpaid, ConditionOperator.GTE, second_turns),
                        _compare(morale, ConditionOperator.LTE, second_morale),
                    ]
                ),
            ),
            _tier(3, _compare(unpaid, ConditionOperator.GTE, third_turns)),
        ],
        choices=[
            EventChoice(
                id="pay_arrears",
                label_hint="Pay the arrears in full",
                order_cost=CHEAP_FIX_COST,
                effects=[
                    _effect(EffectKind.GOLD, -40, on_subject=False),
                    _effect(EffectKind.ARMY_MORALE, 15),
                ],
            ),
            EventChoice(
                id="promise_pay",
                label_hint="Promise back pay once the treasury recovers",
                order_cost=CHEAP_FIX_COST,
                scar_amount=CONCESSION_SCAR,
                effects=[
                    _effect(EffectKind.REPUTATION, -3, on_subject=False),
                    _effect(EffectKind.ARMY_MORALE, 8),
                ],
            ),
            EventChoice(
                id="discipline",
                label_hint="Flog the ringleaders and hold the line",
                order_cost=COSTLY_FIX_COST,
                scar_amount=CRACKDOWN_SCAR,
                effects=[
                    _effect(EffectKind.MANPOWER, -10),
                    _effect(EffectKind.ARMY_MORALE, 10),
                ],
            ),
        ],
        neglect_effects=[
            _effect(EffectKind.ARMY_MORALE, -15),
            _effect(EffectKind.REGION_UNREST, 5),
        ],
    )


def _realm_in_turmoil() -> EventDefinition:
    metric = ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST
    first, second, third = TURMOIL_REGION_COUNTS
    return EventDefinition(
        id="realm_in_turmoil",
        name="Realm in turmoil",
        subject_kind=ConditionScope.FACTION,
        cause_key="realm_in_turmoil",
        cause_metrics=[metric, ConditionMetric.STABILITY],
        tiers=[
            _tier(
                level,
                _compare(
                    metric,
                    ConditionOperator.GTE,
                    count,
                    threshold=TURMOIL_UNREST_THRESHOLD,
                ),
            )
            for level, count in enumerate((first, second, third), start=1)
        ],
        choices=[
            EventChoice(
                id="royal_progress",
                label_hint="Ride the realm to show the crown's strength",
                order_cost=COSTLY_FIX_COST,
                effects=[
                    _effect(EffectKind.STABILITY, 3, on_subject=False),
                    _effect(EffectKind.GOLD, -50, on_subject=False),
                ],
            ),
            EventChoice(
                id="issue_amnesty",
                label_hint="Pardon the agitators and ease the levies",
                order_cost=CHEAP_FIX_COST,
                scar_amount=CONCESSION_SCAR,
                effects=[
                    _effect(EffectKind.UNREST, -5, on_subject=False),
                    _effect(EffectKind.REPUTATION, -2, on_subject=False),
                ],
            ),
        ],
        neglect_effects=[
            _effect(EffectKind.STABILITY, -3, on_subject=False),
            _effect(EffectKind.UNREST, 5, on_subject=False),
        ],
    )


def _season(months: tuple[int, int]) -> list[Condition]:
    first, last = months
    return [
        _compare(ConditionMetric.MONTH, ConditionOperator.GTE, first),
        _compare(ConditionMetric.MONTH, ConditionOperator.LTE, last),
    ]


def _unrest_regions(count: int, threshold: int) -> Comparison:
    return _compare(
        ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST,
        ConditionOperator.GTE,
        count,
        threshold=threshold,
    )


def _bad_harvest() -> EventDefinition:
    season = _season(HARVEST_MONTHS)
    shortage, famine = HUNGER_UNREST_THRESHOLDS
    return EventDefinition(
        id="bad_harvest",
        name="Bad harvest",
        subject_kind=ConditionScope.FACTION,
        cause_key="bad_harvest",
        cause_metrics=[
            ConditionMetric.MONTH,
            ConditionMetric.STABILITY,
            ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST,
        ],
        chance_percent=BAD_HARVEST_CHANCE,
        applies_to_npcs=True,
        tiers=[
            _tier(1, AllOf(conditions=season)),
            _tier(2, AllOf(conditions=[*season, _unrest_regions(1, shortage)])),
            _tier(
                3,
                AllOf(
                    conditions=[
                        *season,
                        _unrest_regions(2, famine),
                        _compare(
                            ConditionMetric.STABILITY,
                            ConditionOperator.LTE,
                            FAMINE_STABILITY_CEILING,
                        ),
                    ]
                ),
            ),
        ],
        choices=[
            EventChoice(
                id="buy_grain",
                label_hint="Buy grain abroad to feed the towns",
                order_cost=CHEAP_FIX_COST,
                effects=[
                    _effect(EffectKind.GOLD, -80, on_subject=False),
                    _effect(EffectKind.UNREST, -3, on_subject=False),
                ],
            ),
            EventChoice(
                id="ration_stores",
                label_hint="Requisition the granaries and ration the bread",
                order_cost=CHEAP_FIX_COST,
                scar_amount=DISASTER_SCAR,
                effects=[
                    _effect(EffectKind.STABILITY, -3, on_subject=False),
                    _effect(EffectKind.UNREST, -4, on_subject=False),
                ],
            ),
        ],
        neglect_effects=[
            _effect(EffectKind.UNREST, 6, on_subject=False),
            _effect(EffectKind.STABILITY, -4, on_subject=False),
            _effect(EffectKind.MANPOWER, -30, on_subject=False),
        ],
    )


def _plague() -> EventDefinition:
    season = _season(PLAGUE_MONTHS)
    first, second, third = PLAGUE_EXHAUSTION_TIERS
    shortage, famine = HUNGER_UNREST_THRESHOLDS
    exhaustion = ConditionMetric.WAR_EXHAUSTION

    def worn(level: int) -> Comparison:
        return _compare(exhaustion, ConditionOperator.GTE, level)

    return EventDefinition(
        id="plague",
        name="Plague",
        subject_kind=ConditionScope.FACTION,
        cause_key="plague",
        cause_metrics=[
            ConditionMetric.MONTH,
            exhaustion,
            ConditionMetric.REGIONS_WITH_UNREST_AT_LEAST,
        ],
        chance_percent=PLAGUE_CHANCE,
        applies_to_npcs=True,
        tiers=[
            _tier(1, AllOf(conditions=[*season, worn(first)])),
            _tier(
                2,
                AllOf(conditions=[*season, worn(second), _unrest_regions(1, shortage)]),
            ),
            _tier(
                3,
                AllOf(conditions=[*season, worn(third), _unrest_regions(2, famine)]),
            ),
        ],
        choices=[
            EventChoice(
                id="pay_physicians",
                label_hint="Pay physicians and bury the dead decently",
                order_cost=CHEAP_FIX_COST,
                effects=[
                    _effect(EffectKind.GOLD, -60, on_subject=False),
                    _effect(EffectKind.MANPOWER, -20, on_subject=False),
                ],
            ),
            EventChoice(
                id="decree_quarantine",
                label_hint="Decree a quarantine of the afflicted towns",
                order_cost=CHEAP_FIX_COST,
                scar_amount=DISASTER_SCAR,
                effects=[
                    _effect(EffectKind.UNREST, 3, on_subject=False),
                    _effect(EffectKind.GOLD, -30, on_subject=False),
                ],
            ),
        ],
        neglect_effects=[
            _effect(EffectKind.MANPOWER, -100, on_subject=False),
            _effect(EffectKind.UNREST, 8, on_subject=False),
            _effect(EffectKind.GOLD, -40, on_subject=False),
        ],
    )


BUILTIN_EVENTS: tuple[EventDefinition, ...] = tuple(
    sorted(
        (
            _tax_grievance(),
            _noble_defiance(),
            _unpaid_mutiny(),
            _realm_in_turmoil(),
        ),
        key=lambda event: event.id,
    )
)
DISASTER_EVENTS: tuple[EventDefinition, ...] = tuple(
    sorted((_bad_harvest(), _plague()), key=lambda event: event.id)
)
DISASTER_EVENT_IDS = frozenset(event.id for event in DISASTER_EVENTS)
BUILTIN_EVENT_IDS = frozenset(event.id for event in BUILTIN_EVENTS) | DISASTER_EVENT_IDS


def effective_events(
    custom_events: list[EventDefinition],
    disabled_builtin_ids: list[str],
    *,
    has_disasters: bool = False,
) -> list[EventDefinition]:
    """Built-ins minus the disabled ones, with same-id custom events replacing
    them, sorted by id so evaluation order is stable. The disaster templates
    join only when ``has_disasters`` is set (worlds on events ruleset 2)."""
    builtins = (*BUILTIN_EVENTS, *DISASTER_EVENTS) if has_disasters else BUILTIN_EVENTS
    by_id = {
        event.id: event
        for event in builtins
        if event.id not in set(disabled_builtin_ids)
    }
    by_id.update({event.id: event for event in custom_events})
    return [by_id[event_id] for event_id in sorted(by_id)]
