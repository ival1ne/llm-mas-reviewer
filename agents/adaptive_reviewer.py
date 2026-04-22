from agents.heavy_reviewer import HeavyReviewer
from agents.lightweight_reviewer import LightweightReviewer


class AdaptiveReviewer:
    def __init__(
        self,
        lightweight_threshold: float = 0.58,
        heavy_regenerate_threshold: float = 0.35,
        low_alignment_threshold: float = 0.5,
        late_stage_threshold: float = 0.55,
        mandatory_heavy_stage: float = 0.7,
    ):
        self.lightweight = LightweightReviewer()
        self.heavy = HeavyReviewer()
        self.lightweight_threshold = lightweight_threshold
        self.heavy_regenerate_threshold = heavy_regenerate_threshold
        self.low_alignment_threshold = low_alignment_threshold
        self.late_stage_threshold = late_stage_threshold
        self.mandatory_heavy_stage = mandatory_heavy_stage

    def review(self, task: str, step: str, context: dict, candidate_output: dict):
        lightweight_result = self.lightweight.review(task, step, context, candidate_output)
        needs_heavy = self._needs_heavy_review(lightweight_result, context)

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
            "trigger": self._trigger_reason(lightweight_result, context),
            "lightweight_review": lightweight_result,
            "heavy_review": heavy_result,
            "final_decision": final_decision,
            "aligned": final_decision["aligned"],
            "score": final_decision["score"],
            "issues": final_decision["issues"],
            "recommendation": final_decision["recommendation"],
        }

    def _needs_heavy_review(self, lightweight_result: dict, context: dict) -> bool:
        if self._is_mandatory_heavy_stage(context):
            return True
        if lightweight_result.get("flag_drift"):
            return True
        if lightweight_result["suspicion_score"] >= self.lightweight_threshold:
            return True
        if lightweight_result["score"] <= self.low_alignment_threshold:
            return True
        if self._is_late_stage(context) and lightweight_result["score"] <= self.late_stage_threshold:
            return True
        return False

    def _trigger_reason(self, lightweight_result: dict, context: dict) -> str:
        if self._is_mandatory_heavy_stage(context):
            return "mandatory_final_stage_heavy"
        if lightweight_result.get("flag_drift"):
            return "lightweight_flagged_drift"
        if lightweight_result["score"] <= self.low_alignment_threshold:
            return "lightweight_low_alignment"
        if self._is_late_stage(context) and lightweight_result["score"] <= self.late_stage_threshold:
            return "lightweight_late_stage_low_alignment"
        return "lightweight_high_suspicion"

    def _merge_results(self, lightweight_result: dict, heavy_result: dict) -> dict:
        heavy_score = heavy_result.get("score", 0.0)
        recommendation = "continue" if heavy_result.get("aligned", False) else "revise"
        if (
            not heavy_result.get("aligned", False)
            and heavy_result.get("recommendation") == "regenerate"
            and heavy_score <= self.heavy_regenerate_threshold
        ):
            recommendation = "regenerate"
        if heavy_result.get("aligned", False):
            merged_issues = heavy_result.get("issues", [])
        else:
            merged_issues = []
            for issue in lightweight_result.get("issues", []) + heavy_result.get("issues", []):
                if issue not in merged_issues:
                    merged_issues.append(issue)

        return {
            "reviewer_type": "adaptive_final",
            "aligned": bool(heavy_result.get("aligned", False)),
            "score": float(heavy_score),
            "issues": merged_issues,
            "recommendation": recommendation,
        }

    def _is_late_stage(self, context: dict) -> bool:
        plan_length = len(context.get("plan", []))
        completed_steps = len(context.get("steps", []))
        if not plan_length:
            return False
        return (completed_steps + 1) / plan_length >= 0.7

    def _is_mandatory_heavy_stage(self, context: dict) -> bool:
        plan_length = len(context.get("plan", []))
        completed_steps = len(context.get("steps", []))
        if not plan_length:
            return False
        return (completed_steps + 1) / plan_length >= self.mandatory_heavy_stage
