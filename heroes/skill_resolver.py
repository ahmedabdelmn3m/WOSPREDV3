from typing import Dict, List
from .hero_loader import HeroLoader

class SkillResolver:
    def __init__(self, loader: HeroLoader = None):
        self.loader = loader or HeroLoader()

    def resolve(self, hero_name: str, star: int, widget: int) -> dict:
        """
        Returns a dict of combat modifiers for this hero at given star/widget level.
        """
        hero = self.loader.get_hero_by_name(hero_name)
        if not hero:
            return {}

        modifiers = {}
        for skill in hero.get("skills", []):
            trigger = skill.get("trigger", "battle_start")
            target = skill.get("target", "all_troops")
            
            # Use star scaling or widget scaling if available
            # If widget > 0 and widget_scaling exists, use that, else star_scaling
            scaling = skill.get("star_scaling", {})
            if str(widget) in skill.get("widget_scaling", {}):
                val = skill["widget_scaling"][str(widget)]
            elif str(star) in scaling:
                val = scaling[str(star)]
            else:
                # Fallback to base value of first effect if no scaling found
                val = skill["effects"][0]["base_value"] if skill.get("effects") else 0

            for effect in skill.get("effects", []):
                stat = effect["stat"]
                key = f"{stat}_{target}_{trigger}"
                modifiers[key] = modifiers.get(key, 0) + val

        return modifiers
