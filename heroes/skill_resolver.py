"""
SkillResolver: Convert hero selections (name, star, widget) into combat modifiers.

This module resolves hero expedition skills into quantifiable combat bonuses that can be
applied to troop stats during battle calculations.

Skill Resolution Process:
1. Load hero data by name
2. Extract expedition skills
3. Look up the value at the requested star level
4. Return a dict of combat modifiers (attack_bonus, defense_bonus, etc.)

Modifier Format:
{
    "attack_bonus": 0.25,           # 25% attack bonus to all troops
    "lethality_bonus": 0.30,        # 30% lethality bonus
    "rally_attack_bonus": 0.15,     # Rally-specific bonuses
    ...
}
"""

from typing import Dict, Optional, List
from .hero_loader import HeroLoader


class SkillResolver:
    """Resolve hero skills into combat modifiers."""

    def __init__(self, loader: HeroLoader = None):
        self.loader = loader or HeroLoader()

    def resolve(
        self,
        hero_name: str,
        star: int = 5,
        widget: int = 5,
    ) -> Dict[str, float]:
        """
        Resolve a hero's expedition skills into combat modifiers.

        Args:
            hero_name: Name of the hero (e.g., "Flint", "Molly")
            star: Star level (1-5, defaults to 5)
            widget: Widget level (1-5, defaults to 5)

        Returns:
            Dict of combat modifiers:
            {
                "attack_bonus": 0.25,
                "defense_bonus": 0.15,
                "lethality_bonus": 0.20,
                "rally_attack_bonus": 0.10,
                ...
            }
        """
        hero = self.loader.get_hero_by_name(hero_name)
        if not hero:
            return {}

        modifiers = {}

        # Process each expedition skill
        for skill in hero.get("expedition_skills", []):
            # Get the value at the requested star level
            star_values = skill.get("star_values", {})
            skill_value = star_values.get(str(star))

            # Skip if value is not available at this star level
            if skill_value is None:
                continue

            # Map skill effect type to modifier key
            effect_type = skill.get("effect_type", "")
            trigger = skill.get("trigger", "battle_start")
            target = skill.get("target", "all_troops")

            # Build modifier key based on effect type and trigger
            modifier_key = self._build_modifier_key(
                effect_type, target, trigger, skill
            )

            if modifier_key:
                # Accumulate modifiers (multiple skills can affect the same stat)
                modifiers[modifier_key] = modifiers.get(modifier_key, 0) + skill_value

        return modifiers

    def _build_modifier_key(
        self,
        effect_type: str,
        target: str,
        trigger: str,
        skill: dict,
    ) -> Optional[str]:
        """
        Build a modifier key from skill properties.

        Effect type examples:
        - all_troops_attack_bonus → attack_bonus
        - infantry_attack_bonus → infantry_attack_bonus
        - rally_attack_bonus → rally_attack_bonus
        - lethality_bonus → lethality_bonus
        """
        # Direct mappings for common effect types
        mapping = {
            "all_troops_attack_bonus": "attack_bonus",
            "all_troops_defense_bonus": "defense_bonus",
            "all_troops_health_bonus": "health_bonus",
            "all_troops_lethality_bonus": "lethality_bonus",
            "infantry_attack_bonus": "infantry_attack_bonus",
            "lancer_attack_bonus": "lancer_attack_bonus",
            "marksman_attack_bonus": "marksman_attack_bonus",
            "infantry_defense_bonus": "infantry_defense_bonus",
            "lancer_defense_bonus": "lancer_defense_bonus",
            "marksman_defense_bonus": "marksman_defense_bonus",
            "rally_attack_bonus": "rally_attack_bonus",
            "rally_lethality_bonus": "rally_lethality_bonus",
            "lethality_bonus": "lethality_bonus",
            "attack_speed_bonus": "attack_speed_bonus",
            "healing_speed_bonus": "healing_speed_bonus",
            "troop_healing_bonus": "troop_healing_bonus",
            "damage_intake_debuff": "damage_intake_debuff",
            "ignite_proc": "ignite_proc",
        }

        return mapping.get(effect_type)

    def resolve_all_heroes(self, star: int = 5, widget: int = 5) -> Dict[str, Dict]:
        """
        Resolve all available heroes into combat modifiers.

        Returns:
            {
                "Flint": {"attack_bonus": 0.25, ...},
                "Molly": {"attack_bonus": 0.15, ...},
                ...
            }
        """
        result = {}
        for hero in self.loader.get_all_heroes():
            hero_name = hero.get("name", "")
            if hero_name:
                result[hero_name] = self.resolve(hero_name, star, widget)
        return result

    def get_hero_info(self, hero_name: str) -> Optional[Dict]:
        """Get full hero information including skills."""
        return self.loader.get_hero_by_name(hero_name)
