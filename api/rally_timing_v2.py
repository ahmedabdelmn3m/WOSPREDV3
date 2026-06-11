"""
Rally Timing Calculator v2 - Simplified Focus

User Input:
- Leader names (Alpha, Beta, Gamma, etc.)
- March times (how long each march takes)
- Rally fill times (5, 10, 15, 20 seconds)
- Desired hitting order (e.g., "Alpha, Beta, Gamma")
- Hit time differences (e.g., "2 seconds apart")

Calculator Output:
- Who launches first
- Who launches after by how many seconds
- Clear launch sequence

Example:
Input:
  - Leaders: ["Alpha", "Beta", "Gamma"]
  - March times: [30, 30, 30]
  - Rally fill: 10
  - Hitting order: ["Alpha", "Beta", "Gamma"]
  - Hit spacing: 2 (seconds)

Output:
  - Alpha launches at 0:00
  - Beta launches at 0:02 (waits 2 seconds after Alpha)
  - Gamma launches at 0:04 (waits 2 seconds after Beta)
  - All hit at the same time (adjusted for march time)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Leader:
    name: str
    march_time: float  # seconds
    rally_fill_time: float  # seconds (5, 10, 15, 20)


@dataclass
class RallyTiming:
    leader_name: str
    launch_time: float  # seconds from first launch
    launch_order: int  # 1st, 2nd, 3rd, etc.
    hit_time: float  # when they hit (march_time + launch_time)
    wait_instruction: str  # "Launch immediately" or "Wait X seconds after [Leader]"


class RallyCalculator:
    """Calculate synchronized rally launch timing."""

    def calculate(
        self,
        leaders: List[Dict],  # [{"name": "Alpha", "march_time": 30, "rally_fill": 10}, ...]
        hitting_order: List[str],  # ["Alpha", "Beta", "Gamma"]
        hit_spacing: float = 0.0,  # seconds between hits (0 = all hit together)
    ) -> Dict:
        """
        Calculate rally launch timing.

        Args:
            leaders: List of leader info with march_time and rally_fill_time
            hitting_order: Desired order of hits (e.g., ["Alpha", "Beta", "Gamma"])
            hit_spacing: Seconds between each hit (0 = simultaneous)

        Returns:
            {
                "success": true,
                "launch_sequence": [
                    {
                        "leader_name": "Alpha",
                        "launch_time": 0.0,
                        "launch_order": 1,
                        "hit_time": 30.0,
                        "wait_instruction": "Launch immediately"
                    },
                    {
                        "leader_name": "Beta",
                        "launch_time": 2.0,
                        "launch_order": 2,
                        "hit_time": 32.0,
                        "wait_instruction": "Wait 2.0 seconds after Alpha launches"
                    },
                    ...
                ],
                "summary": "Alpha launches first. Beta waits 2.0s, then launches. Gamma waits 2.0s after Beta, then launches.",
                "all_hit_time": 30.0
            }
        """
        # Validate inputs
        if not leaders or not hitting_order:
            return {"success": False, "error": "Leaders and hitting order required"}

        # Create leader lookup
        leader_map = {l["name"]: l for l in leaders}

        # Validate hitting order
        for name in hitting_order:
            if name not in leader_map:
                return {"success": False, "error": f"Leader '{name}' not found"}

        # Calculate launch times based on hitting order
        launch_sequence = []
        cumulative_delay = 0.0

        for hit_position, leader_name in enumerate(hitting_order):
            leader = leader_map[leader_name]
            march_time = leader["march_time"]
            rally_fill = leader.get("rally_fill_time", 10)

            # Calculate when this leader needs to launch to hit at the right time
            # If they need to hit at time T, they launch at T - march_time
            desired_hit_time = hit_position * hit_spacing

            # Launch time is adjusted so that march_time + launch_time = desired_hit_time
            launch_time = cumulative_delay
            actual_hit_time = launch_time + march_time

            # Build wait instruction
            if hit_position == 0:
                wait_instruction = "Launch immediately"
            else:
                prev_leader = hitting_order[hit_position - 1]
                wait_seconds = launch_time - launch_sequence[hit_position - 1]["launch_time"]
                wait_instruction = f"Wait {wait_seconds:.1f}s after {prev_leader} launches"

            timing = RallyTiming(
                leader_name=leader_name,
                launch_time=launch_time,
                launch_order=hit_position + 1,
                hit_time=actual_hit_time,
                wait_instruction=wait_instruction,
            )

            launch_sequence.append(timing)
            cumulative_delay += hit_spacing

        # Generate summary
        summary = self._generate_summary(launch_sequence)

        return {
            "success": True,
            "launch_sequence": [self._timing_to_dict(t) for t in launch_sequence],
            "summary": summary,
            "all_hit_time": launch_sequence[-1]["hit_time"] if launch_sequence else 0,
        }

    def _timing_to_dict(self, timing: RallyTiming) -> Dict:
        """Convert RallyTiming to dict."""
        return {
            "leader_name": timing.leader_name,
            "launch_time": round(timing.launch_time, 2),
            "launch_order": timing.launch_order,
            "hit_time": round(timing.hit_time, 2),
            "wait_instruction": timing.wait_instruction,
        }

    def _generate_summary(self, sequence: List[RallyTiming]) -> str:
        """Generate human-readable summary."""
        if not sequence:
            return ""

        lines = []
        for i, timing in enumerate(sequence):
            if i == 0:
                lines.append(f"{timing.leader_name} launches first")
            else:
                prev_name = sequence[i - 1].leader_name
                wait_time = timing.launch_time - sequence[i - 1].launch_time
                lines.append(
                    f"{timing.leader_name} waits {wait_time:.1f}s after {prev_name}, then launches"
                )

        return ". ".join(lines) + "."

    def validate_hitting_order(self, hitting_order: List[str]) -> bool:
        """Validate that hitting order is valid."""
        return len(hitting_order) > 0 and len(set(hitting_order)) == len(hitting_order)


# Singleton
_calculator = RallyCalculator()


def get_rally_calculator() -> RallyCalculator:
    """Get rally calculator instance."""
    return _calculator
