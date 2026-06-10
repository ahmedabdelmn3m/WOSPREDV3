import json
import os
from typing import List, Dict, Optional

class HeroLoader:
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = os.path.join(os.path.dirname(__file__), "hero_data.json")
        self.data_path = data_path
        self.heroes = self._load_data()

    def _load_data(self) -> List[Dict]:
        if not os.path.exists(self.data_path):
            return []
        with open(self.data_path, "r") as f:
            return json.load(f)

    def get_hero_by_name(self, name: str) -> Optional[Dict]:
        for hero in self.heroes:
            if hero["name"].lower() == name.lower():
                return hero
        return None

    def get_all_heroes(self) -> List[Dict]:
        return self.heroes
