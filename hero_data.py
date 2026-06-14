"""
Hero definitions and their expedition skill bonuses.
Skill types:
- attack_only: Provides bonus only to attack.
- attack_and_lethality: Provides equal bonus to both attack and lethality.
"""

from dataclasses import dataclass
from typing import Dict

@dataclass
class Hero:
    name: str
    skill_type: str  # "attack_only" or "attack_and_lethality"
    bonus_pct: float  # Decimal form (0.25 = 25%)

HEROES: Dict[str, Hero] = {
    "Jessie": Hero(
        name="Jessie",
        skill_type="attack_and_lethality",
        bonus_pct=0.25
    ),
    "Jasser": Hero(
        name="Jasser",
        skill_type="attack_and_lethality",
        bonus_pct=0.25
    ),
    "Seo-Yoon": Hero(
        name="Seo-Yoon",
        skill_type="attack_only",
        bonus_pct=0.50
    ),
    "Bahiti": Hero(
        name="Bahiti",
        skill_type="attack_and_lethality",
        bonus_pct=0.20
    ),
    "Sergey": Hero(
        name="Sergey",
        skill_type="attack_only",
        bonus_pct=0.20
    )
}
