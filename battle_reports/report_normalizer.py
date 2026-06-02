class ReportNormalizer:
    @staticmethod
    def normalize(report_data):
        """
        Converts various report formats into the standard internal format
        """
        return {
            "battle_id": report_data.get("id"),
            "attacker": report_data.get("attacker_info"),
            "defender": report_data.get("defender_info"),
            "actual_winner": report_data.get("winner"),
            "rounds": report_data.get("round_details", [])
        }
