# Rally Hero Data Sources and Modeling Policy

Last checked: 2026-08-02

This document records the evidence boundary for the complete rally evaluator.
The evaluator is an auditable comparison model; it does not claim to reproduce
Whiteout Survival's unpublished turn resolver or hidden damage formula.

## Complete Rally Contract

Century Games' [Combat FAQ](https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/8048-combat-faq/?l=en)
defines the skill contribution used by the engine:

- A rally leader fields three heroes and all three Expedition skills from each
  hero contribute: exactly **9 rally-leader skill slots**.
- Exactly four rally members contribute the first Expedition skill of the hero
  at the head of their joining march: exactly **4 joiner skill slots**.
- The engine rejects an incomplete leader march or any joiner contribution count
  other than four. A valid S1-S5 leader march must contain one Legendary
  (internally Mythic-tier) Infantry, one Lancer, and one Marksman hero, each with all three current
  Expedition skills configured.

The current S1-S5 Legendary (internally Mythic-tier) leader pool is:

| Generation | Infantry | Lancer | Marksman |
| --- | --- | --- | --- |
| S1 | Jeronimo, Natalia | Molly | Zinman |
| S2 | Flint | Philly | Alonso |
| S3 | Logan | Mia | Greg |
| S4 | Ahmose | Reina | Lynn |
| S5 | Hector | Norah | Gwen |

Joiner heroes are not required to be Legendary/Mythic-tier. Only their configured first
Expedition skill is eligible for the four joining slots. Joiner widgets and a
joiner's second or third Expedition skills are not applied.

## Source Hierarchy

Skill records in `hero_data.py` use the following evidence order:

1. Century Games' official Combat FAQ for rally contribution, duplicate-skill
   behavior, battle-report visibility, and the distinction between different
   combat-effect subjects.
2. Current hero and exclusive-gear tooltips on the
   [Whiteout Survival Wiki](https://www.whiteoutsurvival.wiki/heroes/) for hero
   type, generation, Expedition skill text and level-5 magnitude, widget
   context, and verified maximum values.
3. Reproducible community tests for behavior that the official FAQ does not
   fully specify. These claims retain a community evidence label and never
   silently become official facts.
4. Disputed or insufficiently tested behavior is marked experimental and is
   excluded from automatic numerical scoring. An explicit opt-in exposes its
   printed magnitude only in the ceiling stress test, never in the floor or
   expected scenario.

Current records follow the post-December-2025 tooltips. Older community pages
may still show pre-rework kits, including changed skills for Jeronimo, Natalia,
Logan, and Hector. Exploration skill text must not be copied into an Expedition
skill record; only battle-facing Expedition skills belong in the rally engine.

Missing or unresolved values remain absent. The app must not invent a percentage,
duration, proc interaction, counter owner, or refresh/stack rule to complete a
hero record.

## Stacking Policy

Century Games confirms that matching rally-member skills can stack in
[the duplicate-skill FAQ](https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/8050-if-the-4-skills-of-the-rally-members-are-the-same-as-the-captain-s-will-the-effects-be-stackable/).
The implementation turns that rule into the following explicit model:

- Contributions add when their operational key is identical: affected side,
  target troop scope, triggering troop scope, and effect type must all match.
  Deterministic skills contribute their full magnitude; a supported conditional
  skill contributes its scenario-weighted magnitude in the expected view.
- Effects with a different subject, effect type, or troop scope remain separate
  equation layers. The model multiplies these distinct layer factors instead of
  merging their percentages.
- Each conditional/proc copy remains an independent audit record. The engine
  never turns four 40% proc skills into a fabricated 160% proc chance. Its
  expected scenario probability-weights each supported record, then adds those
  weighted magnitudes when they share the same operational key.
- Normal-attack and extra-attack event contributions add inside one event-damage
  channel. They are not multiplied into one another because public evidence does
  not establish that one event amplifies every other event.
- Compound skills are decomposed into their real components. For example,
  Philly's first Expedition skill supplies separate Attack and Defense keys.

The same-key addition is anchored by the official duplicate rule. The precise
cross-layer multiplication and defensive reciprocal operator are transparent
community comparison policies, not a published Century Games combat formula.

## Damage Dealt and Damage Taken

Century Games states that skills with different effect subjects are calculated
differently in its [skill-description FAQ](https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/8052-about-skill-descriptions/).
Accordingly, the evaluator does not combine these labels into one additive
percentage:

- **Damage Dealt** is an output-side layer on the attacking force.
- **Increased Damage Taken** is an input-side layer on the affected target.
- **Reduced Damage Taken** and **reduced enemy Damage Dealt** are also retained
  as different defensive subjects.

For comparison scoring, distinct subjects multiply as separate factors. The
defensive score currently uses a reciprocal effective-health index. This is
useful for ranking alternatives, but it remains community-unverified and must
not be presented as the game's exact hidden formula.

## Widgets and Exclusive Gear

The widget Expedition special follows the verified ladder documented in the
[combat stats and special bonuses guide](https://www.whiteoutsurvival.wiki/combat-stats-special-bonuses/):

| Widget level | Expedition special |
| --- | ---: |
| 0-1 | 0% |
| 2-3 | 5% |
| 4-5 | 7.5% |
| 6-7 | 10% |
| 8-9 | 12.5% |
| 10 | 15% |

Odd widget levels upgrade the Exploration-side special; even levels unlock or
upgrade the Expedition-side special. Therefore level 1 has no Expedition
special, while levels 2 and 3 share the same 5% Expedition value.

Each leader widget is applied only in the tooltip's combat context:

- Rally/attacking specials apply in the PvP attack context.
- Defender specials apply in the garrison context.
- A widget at the wrong context remains visible in the audit output but makes no
  numerical contribution.

Only the authoritative level-10 raw Lethality and Health totals are stored.
Exact intermediate raw-stat values for levels 1-9 are not publicly verified, so
the engine returns `null` rather than linearly interpolating them. Observed
battle-report combat bonuses are treated as the baseline and are assumed to
already include raw hero and exclusive-gear stats; those raw values are shown
for audit and are never added a second time. This follows Century Games'
[battle-report visibility guidance](https://centurygames.helpshift.com/hc/en/64-whiteout-survival/faq/8051-what-special-bonuses-are-shown-in-battle-reports/).

## Conditional and Disputed Skills

The engine exposes three scenarios instead of one falsely precise result:

- **Floor:** verified deterministic effects only.
- **Expected:** conditional effects use a documented probability only for a
  supported direct chance/event model, or a clearly identified nominal uptime
  proxy. Duration-unknown and unresolved stateful effects contribute zero here
  even when a tooltip publishes a raw proc chance.
- **Ceiling:** every modeled conditional effect is treated as fully triggered.

These are combat indices, not turn-by-turn guarantees. Durations, skipped
attacks, attack counters, refresh behavior, battle length, and target timing can
make the real outcome differ from the expected proxy.

Important exclusions and caveats include:

- Natalia's `Call of the Wild` is beast-rally-only, so it occupies one of her
  three leader skill slots but contributes nothing in PvP or garrison scoring.
- Zinman's `Bastionist` is a non-combat construction skill. It occupies a leader
  slot but contributes no combat buff.
- Gwen's `Eagle Vision` tooltip magnitude is stored for audit, but public tests
  conflict on effective mode/timing behavior. It is experimental and excluded
  from numerical scoring by default. If `includeDisputedSkills` is explicitly
  enabled, it contributes only to the ceiling stress test; floor and expected
  remain unchanged.
- Skills with unknown duration, counter ownership, refresh behavior, or
  unbounded battle-length stacks retain a warning. Their expected result is zero
  unless the engine has a declared, bounded proxy; it never uses an unstated
  assumption.

## Model Coverage and Normalization

`contract.complete` means that the structural 9+4 contribution rule is
satisfied. It does not mean every one of those 13 skill slots has a validated
numerical channel or that the output is an exact combat forecast. The
`modelCoverage` object therefore reports context exclusions, disputed effects,
expected-uptime unknowns, unsupported mechanics, and unpriced tradeoffs
separately.

The request currently supplies one shared Attack/Defense/Health/Lethality vector
for the formation. Real battle reports can have different values for Infantry,
Lancer, and Marksman. Until the API accepts separate observed vectors per troop
class, the output is labeled `NORMALIZED_SKILL_STACK_INDEX`: it is suitable for
comparing the modeled skill stack, not for predicting exact damage, casualties,
or survivors. For the same reason, an expected scenario containing conditional
defense reports a reciprocal defense-index proxy and leaves the literal expected
incoming-damage multiplier unset.

## Maintenance Checklist

When a hero tooltip or community result changes:

1. Verify that the source describes an **Expedition** skill and the current game
   version.
2. Preserve all three leader skill slots, including contextual or non-combat
   slots that correctly contribute zero in the selected battle context.
3. Split compound skills into components with accurate affected-side, target,
   and triggering-troop scopes.
4. Record activation chance, duration, interval, model status, source, and
   confidence independently. Do not derive one from another.
5. Keep disputed effects experimental until evidence resolves the dispute.
6. Add a focused regression case in `tests/test_rally_evaluation.py`; update
   `tests/test_rally_skills.py` only when shared legacy rally mechanics change.

The complete evaluator is implemented in `core_engine/rally_evaluation.py` and
served by `POST /api/rallies/evaluate`. The joiner-only ranking endpoint remains
`POST /api/rallies/joiner-recommendations`.
