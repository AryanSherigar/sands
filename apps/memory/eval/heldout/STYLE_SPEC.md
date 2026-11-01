# C2b probe style spec

C2b rewrites each C2 probe the way a real player types it into a text adventure. The labels never change; only the wording does.

## What real player turns look like
- Short and unpolished. Most are one line, many under ten words; a few run on with two intents ("ok so go back to the dock and ask the old guy about the thing from before").
- Casual: lowercase starts, missing punctuation, the odd typo, contractions, slang ("wait", "hold on", "lol", "uh", "idk", "kinda").
- Pronouns and shorthand instead of names: "him", "her", "that thing", "the place", "it again", "that guy".
- Players mix speech, action and questions. Match the original's action mode: `say` is something the character says out loud; `do` is an action; `see` is looking or observing; `story` steers the narration.
- They refer to things from earlier without re-explaining them, and they sometimes misremember a detail slightly.

## Hard rules
1. Keep the same intent as the original probe: the answer must still be the same piece of story evidence.
2. Do not reuse the wording of the evidence ("avoid" list). No run of three or more consecutive words may match it, and at most about a quarter of your content words may appear in it. Use synonyms, pronouns or a looser description.
3. Do not copy the original wording.
4. For `vague` probes keep them vague (a pronoun or "it"/"the door"/"him" with no name); do not make them more specific than the original.
5. Never add facts that are not in the original probe or its expected truth. Never answer the question inside the probe.
6. One line, at most 200 characters, no quotation marks around the whole thing, no explanation.
7. Vary style across a batch: do not give every probe the same opener or the same shape.
