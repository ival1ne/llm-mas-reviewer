from agents.heavy_reviewer import HeavyReviewer
from agents.lightweight_reviewer import LightweightReviewer


class AdaptiveReviewer:
    def __init__(
        self,
        lightweight_threshold: float = 0.55,
        heavy_regenerate_threshold: float = 0.35,
    ):
        self.lightweight = LightweightReviewer()
        self.heavy = HeavyReviewer()
        self.lightweight_threshold = lightweight_threshold
        self.heavy_regenerate_threshold = heavy_regenerate_threshold

    def review(self, task: str, step: str, context: dict, candidate_output: dict):
        lightweight_result = self.lightweight.review(task, step, context, candidate_output)
        needs_heavy = self._needs_heavy_review(lightweight_result)

        if not needs_heavy:
            return {
                "reviewer_type": "adaptive",
                "path": "lightweight_only",
                "trigger": None,
                "lightweight_review": lightweight_result,
                "final_decision": lightweight_result,
                "aligned": lightweight_result["aligned"],
                "score": lightweight_result["score"],
                "issues": lightweight_result["issues"],
                "recommendation": lightweight_result["recommendation"],
            }

        heavy_result = self.heavy.review(task, step, context, candidate_output)
        final_decision = self._merge_results(lightweight_result, heavy_result)

        return {
            "reviewer_type": "adaptive",
            "path": "lightweight_then_heavy",
            "trigger": self._trigger_reason(lightweight_result),
            "lightweight_review": lightweight_result,
            "heavy_review": heavy_result,
            "final_decision": final_decision,
            "aligned": final_decision["aligned"],
            "score": final_decision["score"],
            "issues": final_decision["issues"],
            "recommendation": final_decision["recommendation"],
        }

    def _needs_heavy_review(self, lightweight_result: dict) -> bool:
        if lightweight_result["recommendation"] == "regenerate":
            return True
        if lightweight_result["score"] < self.lightweight_threshold:
            return True
        if lightweight_result["issues"]:
            return True
        return False

    def _trigger_reason(self, lightweight_result: dict) -> str:
        if lightweight_result["recommendation"] == "regenerate":
            return "lightweight_requested_regenerate"
        if lightweight_result["issues"]:
            return "lightweight_detected_issues"
        return "lightweight_low_score"

    def _merge_results(self, lightweight_result: dict, heavy_result: dict) -> dict:
        merged_issues = []
        for issue in lightweight_result.get("issues", []) + heavy_result.get("issues", []):
            if issue not in merged_issues:
                merged_issues.append(issue)

        heavy_score = heavy_result.get("score", 0.0)
        recommendation = heavy_result.get("recommendation", "revise")
        if heavy_score <= self.heavy_regenerate_threshold:
            recommendation = "regenerate"

        return {
            "reviewer_type": "adaptive_final",
            "aligned": bool(heavy_result.get("aligned", False)),
            "score": float(heavy_score),
            "issues": merged_issues,
            "recommendation": recommendation,
        }
