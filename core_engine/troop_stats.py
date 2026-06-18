"""
Core troop architecture for WOS Battle Intelligence.

Hierarchy
---------
TroopTypeStats  →  stats + formula for one troop type (Infantry / Lancer / Marksman)
Formation       →  how troops are distributed (e.g. 50 / 20 / 30)
ArmyStats       →  complete army = 3 × TroopTypeStats + Formation + troop_count

All bonuses are stored in DECIMAL form internally.
Public helpers accept percentage values (150.0 for 150 %) and convert automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .damage_model import DamageModel
from joiner_logic import calculate_rally_effective_modifiers
from .defense_model import DefenseModel


# ─────────────────────────────────────────────────────────────────────────────
#  TroopTypeStats
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TroopTypeStats:
    """
    Stats for a single troop type as extracted from a scout screenshot.

    Base values
    -----------
    attack / defense / health / lethality  →  absolute base power of that troop.
    Defaults to 1.0.  Use 1.0 whenever only % bonuses are known from the scout.

    Bonus values  (DECIMAL — stored internally)
    -------------------------------------------
    attack_bonus    =  Σ Attack%    bonuses  (150 % stored as 1.50)
    defense_bonus   =  Σ Defense%   bonuses
    health_bonus    =  Σ Health%    bonuses
    lethality_bonus =  Σ Lethality% bonuses
    """

    # Base combat values
    attack:    float = 1.0
    defense:   float = 1.0
    health:    float = 1.0
    lethality: float = 1.0

    # Σ bonus multipliers (decimal form)
    attack_bonus:    float = 0.0
    defense_bonus:   float = 0.0
    health_bonus:    float = 0.0
    lethality_bonus: float = 0.0

    # ── Verified formulas ────────────────────────────────────────────────

    @property
    def effective_damage(self) -> float:
        """
        damage = (attack × (1 + attack_bonus) × lethality × (1 + lethality_bonus)) / 100
        """
        return DamageModel.calculate(
            self.attack,    self.attack_bonus,
            self.lethality, self.lethality_bonus,
        )

    @property
    def effective_defense(self) -> float:
        """
        defense = (defense × (1 + defense_bonus) × health × (1 + health_bonus)) / 100
        """
        return DefenseModel.calculate(
            self.defense, self.defense_bonus,
            self.health,  self.health_bonus,
        )

    # ── Factories ────────────────────────────────────────────────────────

    @classmethod
    def from_percentages(
        cls,
        attack_pct:    float = 0.0,
        defense_pct:   float = 0.0,
        health_pct:    float = 0.0,
        lethality_pct: float = 0.0,
        attack_base:    float = 1.0,
        defense_base:   float = 1.0,
        health_base:    float = 1.0,
        lethality_base: float = 1.0,
    ) -> TroopTypeStats:
        """
        Create from raw percentage values (e.g. 150.0 for 150 %).
        Converts to decimal form automatically.
        """
        return cls(
            attack=attack_base,
            defense=defense_base,
            health=health_base,
            lethality=lethality_base,
            attack_bonus=attack_pct       / 100.0,
            defense_bonus=defense_pct     / 100.0,
            health_bonus=health_pct       / 100.0,
            lethality_bonus=lethality_pct / 100.0,
        )

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "attack":            self.attack,
            "defense":           self.defense,
            "health":            self.health,
            "lethality":         self.lethality,
            "attack_bonus_pct":  round(self.attack_bonus    * 100, 2),
            "defense_bonus_pct": round(self.defense_bonus   * 100, 2),
            "health_bonus_pct":  round(self.health_bonus    * 100, 2),
            "lethality_bonus_pct": round(self.lethality_bonus * 100, 2),
            "effective_damage":  round(self.effective_damage,  6),
            "effective_defense": round(self.effective_defense, 6),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Formation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Formation:
    """
    Troop distribution as decimal fractions.  Must sum to 1.0.

    Example: 50 % Infantry / 20 % Lancer / 30 % Marksman
             → Formation(infantry=0.50, lancer=0.20, marksman=0.30)
    """
    infantry:  float = 0.50
    lancer:    float = 0.20
    marksman:  float = 0.30

    def validate(self) -> None:
        total = self.infantry + self.lancer + self.marksman
        if abs(total - 1.0) > 0.005:
            raise ValueError(
                f"Formation must sum to 1.0 — got {total:.4f}. "
                f"(infantry={self.infantry}, lancer={self.lancer}, "
                f"marksman={self.marksman})"
            )

    @classmethod
    def from_percentages(
        cls,
        infantry:  float = 50.0,
        lancer:    float = 20.0,
        marksman:  float = 30.0,
    ) -> Formation:
        """Accept percentage values (50, 20, 30) and convert to fractions."""
        return cls(
            infantry=infantry  / 100.0,
            lancer=lancer      / 100.0,
            marksman=marksman  / 100.0,
        )

    def to_dict(self) -> dict:
        return {
            "infantry_pct":  round(self.infantry  * 100, 1),
            "lancer_pct":    round(self.lancer    * 100, 1),
            "marksman_pct":  round(self.marksman  * 100, 1),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  ArmyStats
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArmyStats:
    """
    Complete army definition used by the combat engine.

        3 × TroopTypeStats  (Infantry, Lancer, Marksman)
        +  Formation         (how troops are split)
        +  troop_count       (total troops)
        +  joiners           (list of hero names)

    Army-wide effective values are formation-weighted averages
    of the per-type effective stats.
    """

    name:        str = "Unknown"
    joiners:     List[str] = field(default_factory=list)

    infantry:    TroopTypeStats = field(default_factory=TroopTypeStats)
    lancer:      TroopTypeStats = field(default_factory=TroopTypeStats)
    marksman:    TroopTypeStats = field(default_factory=TroopTypeStats)

    formation:   Formation      = field(default_factory=Formation)
    troop_count: int             = 500_000

    # ── Army-wide effective stats ────────────────────────────────────────

    def _get_effective_damage_for_type(self, troop_type: str, stats: TroopTypeStats) -> float:
        """Apply transparent hero skill layers before calculating damage."""
        modifiers = calculate_rally_effective_modifiers([], self.joiners, [])["modifiers"][troop_type]
        return DamageModel.calculate_with_layers(
            stats.attack,
            stats.attack_bonus + modifiers["attack_up"],
            stats.lethality,
            stats.lethality_bonus + modifiers["lethality_up"],
            damage_up=modifiers["damage_up"],
            attack_damage_up=modifiers["attack_damage_up"],
            damage_taken_down=modifiers["damage_taken_down"],
        )

    def army_damage(self) -> float:
        """
        Weighted damage power across all troop types.

        army_damage = Σ (formation_weight_T × effective_damage_T)
        """
        self.formation.validate()
        f = self.formation
        return (
            f.infantry  * self._get_effective_damage_for_type("infantry", self.infantry)  +
            f.lancer    * self._get_effective_damage_for_type("lancer", self.lancer)    +
            f.marksman  * self._get_effective_damage_for_type("marksman", self.marksman)
        )

    def army_defense(self) -> float:
        """
        Weighted defense power across all troop types.

        army_defense = Σ (formation_weight_T × effective_defense_T)
        """
        self.formation.validate()
        f = self.formation
        return (
            f.infantry  * self.infantry.effective_defense  +
            f.lancer    * self.lancer.effective_defense    +
            f.marksman  * self.marksman.effective_defense
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def troop_breakdown(self) -> Dict[str, int]:
        """Troop count per type based on formation fractions."""
        return {
            "infantry":  int(self.troop_count * self.formation.infantry),
            "lancer":    int(self.troop_count * self.formation.lancer),
            "marksman":  int(self.troop_count * self.formation.marksman),
        }

    def stat_summary(self) -> dict:
        """Full breakdown suitable for API responses and debug display."""
        return {
            "name":             self.name,
            "joiners":          self.joiners,
            "troop_count":      self.troop_count,
            "formation":        self.formation.to_dict(),
            "troop_breakdown":  self.troop_breakdown(),
            "army_damage":      round(self.army_damage(),  8),
            "army_defense":     round(self.army_defense(), 8),
            "infantry":         self.infantry.to_dict(),
            "lancer":           self.lancer.to_dict(),
            "marksman":         self.marksman.to_dict(),
        }

    # ── Factory: build from scout data ───────────────────────────────────

    @classmethod
    def from_scout(
        cls,
        name:        str,
        infantry:    dict,
        lancer:      dict,
        marksman:    dict,
        formation:   dict,
        troop_count: int,
        joiners:     List[str] = None,
    ) -> ArmyStats:
        """
        Build ArmyStats from scout percentage dicts.

        Each troop dict:
        {
            "attack_pct":    150.0,   # +150 % Attack
            "defense_pct":   120.0,
            "health_pct":    200.0,
            "lethality_pct":  80.0,
        }

        Formation dict (decimal fractions):
        {
            "infantry":  0.50,
            "lancer":    0.20,
            "marksman":  0.30,
        }
        """
        def _parse(d: dict) -> TroopTypeStats:
            return TroopTypeStats.from_percentages(
                attack_pct=d.get("attack_pct",    0.0),
                defense_pct=d.get("defense_pct",  0.0),
                health_pct=d.get("health_pct",    0.0),
                lethality_pct=d.get("lethality_pct", 0.0),
            )

        return cls(
            name=name,
            joiners=joiners or [],
            infantry=_parse(infantry),
            lancer=_parse(lancer),
            marksman=_parse(marksman),
            formation=Formation(
                infantry=formation.get("infantry",  0.50),
                lancer=formation.get("lancer",      0.20),
                marksman=formation.get("marksman",  0.30),
            ),
            troop_count=troop_count,
        )
