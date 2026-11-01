# Authoring state-change cases

Each line of a case file is one JSON object matching `StateChangeCase` in `eval/statechange_cases.py` (read it first). A case is a tiny role-playing game scene: a few characters, a few facts that were already established (`prior_facts`), and 1 to 5 turns of play. The extraction system reads the turns and must decide what changed. Cases test whether it retires the right old facts, leaves the right ones alone, and refuses to record negations or refused changes as facts.

## Rules for every case
- Self-contained. 1 to 3 entities (people, places or objects; the player is added automatically as "The Wanderer" and must not be listed). 1 to 5 turns. Each turn has an `action` (what the player says or does, first person) and `narration` (what the narrator says, 2 to 4 sentences, second person for the player, past or present tense, concrete detail).
- Prior facts are `subject predicate object_literal` with a short snake_case predicate. Mix predicates. Single-valued ones: located_in, lives_in, costs, leads, run_by, holds, is_at, owned_by. Multi-valued or unlisted ones: carries, wears, keeps, guards, allied_with, fears, wants, knows, hides, sells, repairs, studies. Use a different predicate wording in the narration than the stored predicate where natural (stored `keeps` -> narration says the object is now somewhere else).
- Do not use game-tracked numbers such as health, gold or stats. Story facts only.
- Vary genre and names across cases (fantasy, space, noir, western, horror, heist, school, seafaring). Do not reuse names or objects between cases.
- `expect.required[*].words`: two or three distinctive lowercase words that any correct fact about the new information would contain, taken from the narration. `subject` is an entity key or null.
- `expect.forbidden[*].words`: two or three words of a proposition that must NOT be stored as a true fact.
- `expect.superseded`: keys of prior facts the narration makes untrue. `expect.kept`: keys of prior facts that stay true. Every prior fact should appear in exactly one of the two lists unless it is irrelevant filler.
- Never let the narration say "replaces", "supersedes", "no longer true" or similar meta language. The change must be shown as story.
- Never put an answer hint in `note`; it is a one-line human description only.

## Case shape (example)
{"case_id":"chg_00","category":"change","note":"Innkeeper changes","entities":[{"key":"hobb","name":"Hobb","aliases":["the innkeeper"]},{"key":"inn","name":"the Wet Rope","aliases":[]}],"prior_facts":[{"key":"runs","subject":"inn","predicate":"run_by","object_literal":"Hobb"},{"key":"cellar","subject":"inn","predicate":"has","object_literal":"a flooded cellar"}],"turns":[{"action":"I ask who is behind the bar.","narration":"Hobb's widow Tamsin wipes the counter. Hobb died in the spring, and the Wet Rope is hers now."}],"expect":{"superseded":["runs"],"kept":["cellar"],"required":[{"subject":"inn","words":["tamsin"]}],"forbidden":[]}}

Validate your file with (from apps/memory):
PYTHONPATH=. .venv/bin/python -c "from pathlib import Path; from eval.statechange_cases import load_cases; print(len(load_cases(Path('eval/statechange/parts/NAME.jsonl'))))"
