"""
SkillEngine — stub for hero skill effects.

Currently a no-op. Hero skill integration is planned for V2.
When implemented, this will:
  - Fire on_round_start events per hero
  - Return damage/defense multipliers based on active skills
  - Handle cooldowns and durations
"""


class SkillEngine:

    def trigger(self, event: str, attacker, defender, round_num: int) -> None:
        """Fire a combat event. No-op in V1."""
        pass

    def get_modifiers(self, army, stat: str) -> float:
        """Return stat multiplier from active skills. Always 1.0 in V1."""
        return 1.0
