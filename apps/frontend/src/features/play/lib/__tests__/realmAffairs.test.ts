import { describe, expect, it } from "vitest";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import { buildRealmAffairGroups } from "../realmAffairs";

const ME = DEFAULT_PREVIEW_WORLD.my_faction.id;
const RIVALS = [
  { faction_id: "ash", name: "House Ashford", relation: "peace", treasury_range: { low: 0, high: 1 }, manpower_range: { low: 0, high: 1 } },
  { faction_id: "car", name: "House Carrow", relation: "peace", treasury_range: { low: 0, high: 1 }, manpower_range: { low: 0, high: 1 } },
];

const base = { ...DEFAULT_PREVIEW_WORLD, rivals: RIVALS };

describe("buildRealmAffairGroups", () => {
  it("returns nothing for a quiet realm", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      alliances: [],
      vassalages: [],
      coalitions: [],
      wars: [],
      own_prisoners: [],
      own_hostages: [],
      subsidies: [],
      mobilization: null,
    });

    expect(groups).toEqual([]);
  });

  it("offers a confirmed denounce on an alliance and names the partner", () => {
    const [group] = buildRealmAffairGroups({
      ...base,
      alliances: [{ id: "al-1", partner_id: "ash", alliance_type: "defensive", is_separate_peace_banned: true }],
    });

    expect(group?.affairs[0]?.title).toBe("Allied with House Ashford");
    const action = group?.affairs[0]?.actions[0];
    expect(action?.order).toEqual({ kind: "denounce_alliance", faction_id: ME, alliance_id: "al-1" });
    expect(action?.confirmation?.confirmLabel).toBe("Denounce");
  });

  it("gives an overlord release and annex, but a vassal no actions", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      vassalages: [
        { id: "v1", overlord_id: ME, vassal_id: "ash", tribute_share_percent: 20, levy_share_percent: 10, is_foreign_policy_controlled: false, has_garrison_rights: false },
        { id: "v2", overlord_id: "car", vassal_id: ME, tribute_share_percent: 30, levy_share_percent: 5, is_foreign_policy_controlled: true, has_garrison_rights: false },
      ],
    });
    const affairs = groups.find((group) => group.id === "vassals")?.affairs ?? [];

    expect(affairs[0]?.actions.map((action) => action.label)).toEqual(["Make a demand", "Release", "Annex"]);
    expect(affairs[1]?.title).toBe("You serve House Carrow");
    expect(affairs[1]?.actions).toEqual([]);
  });

  it("lets the player mediate other realms' wars only, and handle held prisoners", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      wars: [
        { id: "w1", attacker_id: ME, defender_id: "ash" },
        { id: "w2", attacker_id: "ash", defender_id: "car" },
      ],
      own_prisoners: [{ id: "p1", name: "Lord Brand", title: "Captain", origin_faction_id: "ash", ransom_value_gold: 300, sentence_ends_turn: null }],
    });
    const wars = groups.find((group) => group.id === "wars")?.affairs ?? [];
    const prisoners = groups.find((group) => group.id === "prisoners")?.affairs ?? [];

    expect(wars[0]?.actions).toEqual([]);
    expect(wars[1]?.actions[0]?.order).toEqual({ kind: "mediate", faction_id: ME, war_id: "w2" });
    expect(prisoners[0]?.actions.map((action) => action.label)).toEqual(["Ransom", "Exchange", "Release", "Execute"]);
    expect(prisoners[0]?.actions[3]?.confirmation).toBeDefined();
  });

  it("only offers to cut a subsidy the player pays", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      subsidies: [
        { id: "s1", payer_id: ME, receiver_id: "ash", war_id: "w1", amount_per_turn: 50, turns_left: 4 },
        { id: "s2", payer_id: "car", receiver_id: ME, war_id: "w1", amount_per_turn: 20, turns_left: 2 },
      ],
    });
    const affairs = groups.find((group) => group.id === "subsidies")?.affairs ?? [];

    expect(affairs[0]?.actions[0]?.order).toEqual({ kind: "cut_subsidy", faction_id: ME, subsidy_id: "s1" });
    expect(affairs[1]?.actions).toEqual([]);
  });

  it("lists active sworn oaths from both sides without actions", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      sworn_promises: [
        { commitment_id: "c1", promisor_id: ME, beneficiary_id: "ash", promise: "never_attack_faction", subject_id: "car", end_turn: 20 },
        { commitment_id: "c2", promisor_id: "car", beneficiary_id: ME, promise: "spare_prisoners", end_turn: null },
      ],
    });
    const oaths = groups.find((group) => group.id === "oaths")?.affairs ?? [];

    expect(oaths[0]?.title).toBe("You swore to House Ashford never to attack House Carrow");
    expect(oaths[0]?.detail).toBe("In force until turn 20");
    expect(oaths[1]?.title).toBe("House Carrow swore to you to spare prisoners");
    expect(oaths.every((oath) => oath.actions.length === 0)).toBe(true);
  });

  it("offers a mobilize order only at war and not while already mobilized", () => {
    const atWar = buildRealmAffairGroups({ ...base, wars: [{ id: "w1", attacker_id: ME, defender_id: "ash" }] });
    const other = atWar.find((group) => group.id === "other")?.affairs ?? [];
    expect(other[0]?.actions[0]?.order).toEqual({ kind: "mobilize", faction_id: ME });
    expect(other[0]?.actions[0]?.confirmation).toBeDefined();

    const mobilized = buildRealmAffairGroups({ ...base, wars: [{ id: "w1", attacker_id: ME, defender_id: "ash" }], mobilization: { turns_left: 3 } });
    const mobilizedOther = mobilized.find((group) => group.id === "other")?.affairs ?? [];
    expect(mobilizedOther[0]?.actions).toEqual([]);

    expect(buildRealmAffairGroups({ ...base, wars: [], mobilization: null }).some((group) => group.id === "other")).toBe(false);
  });

  it("offers a subsidy form for a war the player is not in, with both sides as receivers", () => {
    const groups = buildRealmAffairGroups({ ...base, wars: [{ id: "w2", attacker_id: "ash", defender_id: "car" }] });
    const form = groups.find((group) => group.id === "wars")?.affairs[0]?.actions[1]?.form;

    expect(form).toEqual({
      kind: "subsidize",
      warId: "w2",
      receivers: [{ id: "ash", label: "House Ashford" }, { id: "car", label: "House Carrow" }],
    });
  });

  it("offers coalition targets an appease form listing only claimed regions of theirs", () => {
    const regions = DEFAULT_PREVIEW_WORLD.regions.slice(0, 2).map((region, index) => ({
      ...region,
      owner_id: ME,
      detail: { ...(region.detail ?? ({} as never)), claimant_ids: index === 0 ? ["ash"] : [] },
    }));
    const groups = buildRealmAffairGroups(
      { ...base, regions, coalitions: [{ id: "co1", target_id: ME, member_ids: ["ash", "car"], expires_turn: 9 }] },
      { [regions[0]!.region_id]: "Dunmere" },
    );
    const form = groups.find((group) => group.id === "coalitions")?.affairs[0]?.actions[0]?.form;

    expect(form?.kind).toBe("appease");
    if (form?.kind !== "appease") return;
    expect(form.claimedRegionsByMember["ash"]).toEqual([{ id: regions[0]!.region_id, label: "Dunmere" }]);
    expect(form.claimedRegionsByMember["car"]).toEqual([]);
  });

  it("gives an overlord a demand form carrying the treaty shares", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      vassalages: [{ id: "v1", overlord_id: ME, vassal_id: "ash", tribute_share_percent: 20, levy_share_percent: 10, is_foreign_policy_controlled: false, has_garrison_rights: false }],
    });
    const form = groups.find((group) => group.id === "vassals")?.affairs[0]?.actions[0]?.form;

    expect(form).toEqual({ kind: "vassal_demand", vassalageId: "v1", tributePercent: 20, levyPercent: 10 });
  });

  it("lists resolved oaths with how they ended", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      sworn_promise_history: [
        { commitment_id: "c9", promisor_id: ME, beneficiary_id: "ash", promise: "never_attack_faction", outcome: "breached", end_turn: 12 },
        { commitment_id: "c8", promisor_id: "car", beneficiary_id: ME, promise: "spare_prisoners", outcome: "fulfilled" },
      ],
    });
    const history = groups.find((group) => group.id === "oath-history")?.affairs ?? [];

    expect(history.map((item) => item.detail)).toEqual(["Broken", "Kept to the end"]);
    expect(history[0]?.title).toBe("You swore to House Ashford never to attack");
  });

  it("shows a war's outlook and goal slots as words, never scores", () => {
    const groups = buildRealmAffairGroups({
      ...base,
      wars: [{ id: "w1", attacker_id: ME, defender_id: "ash", outlook: "leading", goal_slots: 2 }],
    });
    const war = groups.find((group) => group.id === "wars")?.affairs[0];

    expect(war?.detail).toBe("War #w1; you are winning; 2 war goals to claim");
  });
});
