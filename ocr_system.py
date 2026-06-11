"""
OCR System: Extract troop stats from WOS scout screenshots using Claude Vision API.

This module handles:
1. Image upload/validation
2. Claude Vision API calls
3. Stat extraction and parsing
4. Result formatting for battle predictor

Supported stat types:
- Attack, Defense, Health, Lethality
- Troop type breakdown (Infantry, Lancer, Marksman)
- Formation percentages
"""

import base64
import json
import os
import re
from typing import Dict, Optional, Tuple
import httpx


class OCRSystem:
    """Extract troop stats from WOS screenshots using Claude Vision API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OCR system with Claude API key."""
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "CLAUDE_API_KEY environment variable not set. "
                "Get it from https://console.anthropic.com/"
            )
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-5-sonnet-20241022"

    def extract_stats_from_image(
        self, image_path: str, image_format: str = "auto"
    ) -> Dict:
        """
        Extract troop stats from a WOS scout screenshot.

        Args:
            image_path: Path to image file (local or URL)
            image_format: Image format ('jpeg', 'png', 'gif', 'webp', or 'auto')

        Returns:
            {
                "success": true,
                "stats": {
                    "infantry": {"attack_pct": 150, "defense_pct": 120, ...},
                    "lancer": {...},
                    "marksman": {...},
                    "formation": {"infantry": 0.50, "lancer": 0.20, "marksman": 0.30},
                    "troop_count": 50000
                },
                "confidence": 0.95,
                "raw_text": "..."
            }
        """
        try:
            # Encode image
            image_data = self._encode_image(image_path)
            if not image_data:
                return {"success": False, "error": "Failed to encode image"}

            # Determine media type
            if image_format == "auto":
                image_format = self._detect_format(image_path)
            media_type = f"image/{image_format}"

            # Call Claude Vision API
            response = self._call_claude_vision(image_data, media_type)
            if not response:
                return {"success": False, "error": "Claude API call failed"}

            # Parse response
            extracted_text = response.get("content", [{}])[0].get("text", "")
            parsed_stats = self._parse_stats_from_text(extracted_text)

            return {
                "success": True,
                "stats": parsed_stats,
                "confidence": self._calculate_confidence(parsed_stats),
                "raw_text": extracted_text,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encode image to base64."""
        try:
            if image_path.startswith("http://") or image_path.startswith("https://"):
                # For URLs, we'd need to download first
                # For now, return None to indicate URL handling needed
                return None
            
            with open(image_path, "rb") as f:
                return base64.standard_b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    def _detect_format(self, image_path: str) -> str:
        """Detect image format from file extension."""
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        valid_formats = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
        return valid_formats.get(ext, "jpeg")

    def _call_claude_vision(self, image_data: str, media_type: str) -> Optional[Dict]:
        """Call Claude Vision API to analyze image."""
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": self._get_extraction_prompt(),
                            },
                        ],
                    }
                ],
            }

            with httpx.Client() as client:
                response = client.post(self.api_url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    def _get_extraction_prompt(self) -> str:
        """Get the prompt for Claude to extract stats."""
        return """
Extract troop statistics from this Whiteout Survival scout screenshot.

Return a JSON object with this structure:
{
    "infantry": {
        "attack_pct": <number>,
        "defense_pct": <number>,
        "health_pct": <number>,
        "lethality_pct": <number>
    },
    "lancer": {
        "attack_pct": <number>,
        "defense_pct": <number>,
        "health_pct": <number>,
        "lethality_pct": <number>
    },
    "marksman": {
        "attack_pct": <number>,
        "defense_pct": <number>,
        "health_pct": <number>,
        "lethality_pct": <number>
    },
    "formation": {
        "infantry": <decimal 0-1>,
        "lancer": <decimal 0-1>,
        "marksman": <decimal 0-1>
    },
    "troop_count": <number>
}

If any stat is not visible, use null. Percentages should be raw numbers (150 for 150%).
"""

    def _parse_stats_from_text(self, text: str) -> Dict:
        """Parse Claude's response into structured stats."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass

        # Return empty structure if parsing fails
        return {
            "infantry": {"attack_pct": None, "defense_pct": None, "health_pct": None, "lethality_pct": None},
            "lancer": {"attack_pct": None, "defense_pct": None, "health_pct": None, "lethality_pct": None},
            "marksman": {"attack_pct": None, "defense_pct": None, "health_pct": None, "lethality_pct": None},
            "formation": {"infantry": 0.50, "lancer": 0.20, "marksman": 0.30},
            "troop_count": None,
        }

    def _calculate_confidence(self, stats: Dict) -> float:
        """Calculate confidence score based on completeness of extracted stats."""
        if not stats:
            return 0.0

        total_fields = 0
        filled_fields = 0

        for troop_type in ["infantry", "lancer", "marksman"]:
            if troop_type in stats:
                for stat in ["attack_pct", "defense_pct", "health_pct", "lethality_pct"]:
                    total_fields += 1
                    if stats[troop_type].get(stat) is not None:
                        filled_fields += 1

        if total_fields == 0:
            return 0.0

        return filled_fields / total_fields


# ─────────────────────────────────────────────────────────────────────────────
#  Singleton instance
# ─────────────────────────────────────────────────────────────────────────────

_ocr_system = None


def get_ocr_system() -> OCRSystem:
    """Get or create OCR system singleton."""
    global _ocr_system
    if _ocr_system is None:
        _ocr_system = OCRSystem()
    return _ocr_system
