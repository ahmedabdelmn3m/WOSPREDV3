"""
TurnResolver — executes one round of combat between two ArmyStats objects.

Round sequence (matches spec):
 1. Trigger hero skills (on_round_start)
 2. Apply skill modifiers (damage / defense multipliers)
 3. Calculate army-wide effective damage and defense
 4. Calculate damage penetration ratio  →  attacker_damage / defender_defense
 5. Calculate casualties for each side
 6. Apply casualties to troop counts
 7. Return full round result dict

Casualty formula
----------------
casualties = troop_count × min(penetration × casualty_rate, 1.0)

penetration  =  attacker_army_damage / defender_army_defense

casualty_rate default: 0.05  (UNVERIFIED — placeholder to be calibrated
from battle report data in V2 learning engine)
"""

from .troop_stats import ArmyStats

DEFAULT_CASUALTY_RATE = 0.05   # 5 % of troops lost per penetration unit (unverified)


class TurnResolver:

    def __init__(
        self,
        casualty_rate: float = DEFAULT_CASUALTY_RATE,
        skill_engine=None,
    ):
        self.casualty_rate = casualty_rate
        self.skill_engine  = skill_engine

    # ─────────────────────────────────────────────────────────────────────
    #  Public
    # ─────────────────────────────────────────────────────────────────────

    def resolve_turn(
        self,
        attacker: ArmyStats,
        defender: ArmyStats,
        round_num: int,
    ) -> dict:
        """
        Execute one combat round.  Mutates troop_count on both armies.
        Returns a dict with full round detail.
        """

        # ── 1. Skill triggers ────────────────────────────────────────────
        if self.skill_engine:
            self.skill_engine.trigger("on_round_start", attacker, defender, round_num)

        # ── 2. Skill modifiers ────────────────────────────────────────────
        atk_dmg_mod = self._mod(attacker, "damage")
        def_dmg_mod = self._mod(defender, "damage")
        atk_def_mod = self._mod(attacker, "defense")
        def_def_mod = self._mod(defender, "defense")

        # ── 3. Army-wide effective stats ──────────────────────────────────
        atk_damage  = attacker.army_damage()  * atk_dmg_mod
        def_damage  = defender.army_damage()  * def_dmg_mod
        atk_defense = attacker.army_defense() * atk_def_mod
        def_defense = defender.army_defense() * def_def_mod

        # ── 4. Penetration ratios ─────────────────────────────────────────
        # How much of the attacker's damage punches through the defender's defense.
        # A ratio > 1.0 means the attacker deals more damage than the defender absorbs.
        atk_penetration = atk_damage / def_defense if def_defense > 0 else float("inf")
        def_penetration = def_damage / atk_defense if atk_defense > 0 else float("inf")

        # ── 5. Casualties ─────────────────────────────────────────────────
        # Cap at 1.0 so troops never go negative in a single round.
        def_casualties = int(
            defender.troop_count * min(atk_penetration * self.casualty_rate, 1.0)
        )
        atk_casualties = int(
            attacker.troop_count * min(def_penetration * self.casualty_rate, 1.0)
        )

        # ── 6. Apply casualties ───────────────────────────────────────────
        defender.troop_count = max(0, defender.troop_count - def_casualties)
        attacker.troop_count = max(0, attacker.troop_count - atk_casualties)

        # ── 7. Round result ───────────────────────────────────────────────
        return {
            "round": round_num,
            "attacker": {
                "name":          attacker.name,
                "damage":        round(atk_damage,        8),
                "defense":       round(atk_defense,       8),
                "penetration":   round(atk_penetration,   8),
                "casualties":    atk_casualties,
                "remaining":     attacker.troop_count,
            },
            "defender": {
                "name":          defender.name,
                "damage":        round(def_damage,        8),
                "defense":       round(def_defense,       8),
                "penetration":   round(def_penetration,   8),
                "casualties":    def_casualties,
                "remaining":     defender.troop_count,
            },
        }

    # ─────────────────────────────────────────────────────────────────────
    #  Private
    # ─────────────────────────────────────────────────────────────────────

    def _mod(self, army: ArmyStats, stat: str) -> float:
        """Return skill modifier, default 1.0 if no skill engine is set."""
        if not self.skill_engine:
            return 1.0
        return self.skill_engine.get_modifiers(army, stat)
