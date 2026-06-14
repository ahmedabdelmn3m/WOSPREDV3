"""
PresetManager — stores named army configurations.

V1 storage: in-memory dict (resets on server restart).
Presets are serialised to the same JSON format the frontend's
localStorage uses, so the client and server stay compatible.
"""

from __future__ import annotations
from typing import Optional, List
from .troop_stats import ArmyStats, TroopTypeStats, Formation


class PresetManager:
    """Thread-safe in-memory preset store for V1."""

    def __init__(self):
        self._presets: dict[str, dict] = {}

    # ─────────────────────────────────────────────────────────────────────
    #  CRUD
    # ─────────────────────────────────────────────────────────────────────

    def save(self, name: str, army: ArmyStats) -> dict:
        """Serialise and store a preset.  Returns the stored dict."""
        serialised = self._serialise(name, army)
        self._presets[name] = serialised
        return serialised

    def save_raw(self, name: str, raw: dict) -> dict:
        """Store a raw preset dict as sent by the frontend."""
        raw["name"] = name
        self._presets[name] = raw
        return raw

    def load(self, name: str) -> Optional[ArmyStats]:
        """Return an ArmyStats for the preset, or None if it doesn't exist."""
        raw = self._presets.get(name)
        return self._deserialise(raw) if raw else None

    def load_raw(self, name: str) -> Optional[dict]:
        """Return the raw dict for the preset (used by API responses)."""
        return self._presets.get(name)

    def list(self) -> List[dict]:
        """List all presets as raw dicts."""
        return list(self._presets.values())

    def delete(self, name: str) -> bool:
        if name in self._presets:
            del self._presets[name]
            return True
        return False

    def exists(self, name: str) -> bool:
        return name in self._presets

    # ─────────────────────────────────────────────────────────────────────
    #  Serialisation helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialise(name: str, army: ArmyStats) -> dict:
        def _troop(t: TroopTypeStats) -> dict:
            return {
                "attack_pct":    round(t.attack_bonus    * 100, 2),
                "defense_pct":   round(t.defense_bonus   * 100, 2),
                "health_pct":    round(t.health_bonus    * 100, 2),
                "lethality_pct": round(t.lethality_bonus * 100, 2),
            }
        return {
            "name":        name,
            "joiners":     army.joiners,
            "troop_count": army.troop_count,
            "formation": {
                "infantry":  army.formation.infantry,
                "lancer":    army.formation.lancer,
                "marksman":  army.formation.marksman,
            },
            "infantry":  _troop(army.infantry),
            "lancer":    _troop(army.lancer),
            "marksman":  _troop(army.marksman),
        }

    @staticmethod
    def _deserialise(data: dict) -> ArmyStats:
        return ArmyStats.from_scout(
            name=data.get("name", "Preset"),
            joiners=data.get("joiners", []),
            infantry=data["infantry"],
            lancer=data["lancer"],
            marksman=data["marksman"],
            formation=data["formation"],
            troop_count=data.get("troop_count", 500_000),
        )
