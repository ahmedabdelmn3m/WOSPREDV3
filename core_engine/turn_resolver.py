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

import random
from .troop_stats import ArmyStats
from .counter_system import calculate_cross_damage
from heroes.skill_resolver import SkillResolver

DEFAULT_CASUALTY_RATE = 0.05   # 5 % of troops lost per penetration unit (unverified)


class TurnResolver:

    def __init__(
        self,
        casualty_rate: float = DEFAULT_CASUALTY_RATE,
        skill_engine=None,
    ):
        self.casualty_rate = casualty_rate
        self.skill_engine  = skill_engine
        self.skill_resolver = SkillResolver()
        self._atk_hero_mods = {}
        self._def_hero_mods = {}

    def _prepare_hero_modifiers(self, army: ArmyStats) -> dict:
        """Resolve all hero skills into a flat dict of modifiers."""
        all_mods = {}
        for hero in army.heroes:
            hero_mods = self.skill_resolver.resolve(hero.name, hero.stars, hero.widget)
            for k, v in hero_mods.items():
                all_mods[k] = all_mods.get(k, 0) + v
        return all_mods

    def _apply_hero_mods(self, army: ArmyStats, mods: dict, trigger: str):
        """Apply modifiers of a specific trigger type to the army stats."""
        for troop_type in ['infantry', 'lancer', 'marksman']:
            stats = getattr(army, troop_type)
            
            # Apply attack_bonus
            stats.attack_bonus += mods.get(f"attack_bonus_{troop_type}_{trigger}", 0)
            stats.attack_bonus += mods.get(f"attack_bonus_all_troops_{trigger}", 0)
            
            # Apply defense_bonus
            stats.defense_bonus += mods.get(f"defense_bonus_{troop_type}_{trigger}", 0)
            stats.defense_bonus += mods.get(f"defense_bonus_all_troops_{trigger}", 0)
            
            # Apply health_bonus
            stats.health_bonus += mods.get(f"health_bonus_{troop_type}_{trigger}", 0)
            stats.health_bonus += mods.get(f"health_bonus_all_troops_{trigger}", 0)
            
            # Apply lethality_bonus
            stats.lethality_bonus += mods.get(f"lethality_bonus_{troop_type}_{trigger}", 0)
            stats.lethality_bonus += mods.get(f"lethality_bonus_all_troops_{trigger}", 0)

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
        
        # ── 0. Init hero mods on round 1 ──────────────────────────────────
        if round_num == 1:
            self._atk_hero_mods = self._prepare_hero_modifiers(attacker)
            self._def_hero_mods = self._prepare_hero_modifiers(defender)
            
            # Apply battle_start modifiers once
            self._apply_hero_mods(attacker, self._atk_hero_mods, "battle_start")
            self._apply_hero_mods(defender, self._def_hero_mods, "battle_start")

        # ── 1. Skill triggers ────────────────────────────────────────────
        # Apply round_start modifiers
        self._apply_hero_mods(attacker, self._atk_hero_mods, "round_start")
        self._apply_hero_mods(defender, self._def_hero_mods, "round_start")
        
        # Apply proc modifiers (with probability)
        # Note: Currently schema doesn't have 'proc_chance', but we handle it for future
        for k, v in self._atk_hero_mods.items():
            if "_proc" in k:
                # For now, assume 10% proc if not specified
                if random.random() < 0.10:
                    # Apply this specific proc mod
                    pass 

        if self.skill_engine:
            self.skill_engine.trigger("on_round_start", attacker, defender, round_num)

        # ── 2. Skill modifiers ────────────────────────────────────────────
        atk_dmg_mod = self._mod(attacker, "damage")
        def_dmg_mod = self._mod(defender, "damage")
        atk_def_mod = self._mod(attacker, "defense")
        def_def_mod = self._mod(defender, "defense")

        # ── 3. Army-wide effective stats ──────────────────────────────────
        # USE COUNTER SYSTEM FOR DAMAGE
        atk_damage  = calculate_cross_damage(attacker, defender) * atk_dmg_mod
        def_damage  = calculate_cross_damage(defender, attacker) * def_dmg_mod
        
        atk_defense = attacker.army_defense() * atk_def_mod
        def_defense = defender.army_defense() * def_def_mod

        # ── 4. Penetration ratios ─────────────────────────────────────────
        atk_penetration = atk_damage / def_defense if def_defense > 0 else float("inf")
        def_penetration = def_damage / atk_defense if atk_defense > 0 else float("inf")

        # ── 5. Casualties ─────────────────────────────────────────────────
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
