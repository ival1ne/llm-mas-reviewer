import math
import re
from collections import Counter

from core.prompt_utils import compact_candidate_output


class LightweightReviewer:
    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "with",
    }

    SYNONYM_MAP = {
        "authentication": "auth",
        "authorize": "auth",
        "authorized": "auth",
        "authorization": "auth",
        "login": "auth",
        "signin": "auth",
        "signup": "auth",
        "register": "auth",
        "registration": "auth",
        "jwt": "auth",
        "endpoint": "api",
        "endpoints": "api",
        "route": "api",
        "routes": "api",
        "crud": "crud",
        "create": "crud",
        "read": "crud",
        "update": "crud",
        "delete": "crud",
        "postgres": "db",
        "postgresql": "db",
        "database": "db",
        "fastapi": "api",
        "validation": "validate",
        "validator": "validate",
        "errors": "error",
        "exceptions": "error",
    }

    IMPORTANT_TOKENS = {"auth", "db", "crud", "api", "task", "user", "admin"}
    GENERIC_STEP_TOKENS = {
        "implement",
        "build",
        "create",
        "write",
        "setup",
        "ensure",
        "handle",
        "using",
        "backend",
        "application",
        "service",
        "system",
        "support",
        "local",
        "testing",
        "necessary",
        "dependency",
        "feature",
    }

    def review(self, task: str, step: str, context: dict, candidate_output: dict):
        features = self._extract_features(task, step, context, candidate_output)
        issues = self._collect_issues(features)
        suspicion_score = self._compute_suspicion(features, issues)
        aligned_score = self._compute_alignment(features)

        return {
            "reviewer_type": "lightweight",
            "aligned": aligned_score >= 0.5 and suspicion_score < 0.55,
            "score": round(aligned_score, 3),
            "issues": issues,
            "recommendation": "continue",
            "flag_drift": suspicion_score >= 0.55,
            "suspicion_score": round(suspicion_score, 3),
            "features": {
                key: round(value, 3) if isinstance(value, float) else value
                for key, value in features.items()
            },
        }

    def _extract_features(
        self, task: str, step: str, context: dict, candidate_output: dict
    ) -> dict:
        compact_candidate = compact_candidate_output(candidate_output)
        candidate_text = " ".join(
            [
                compact_candidate.get("summary", ""),
                " ".join(compact_candidate.get("decisions", [])),
                " ".join(compact_candidate.get("artifacts", [])),
                compact_candidate.get("code_excerpt", ""),
            ]
        )
        summary_text = " ".join(
            [
                compact_candidate.get("summary", ""),
                " ".join(compact_candidate.get("decisions", [])),
                " ".join(compact_candidate.get("artifacts", [])),
            ]
        )

        previous_decisions = []
        for prev_step in context.get("steps", []):
            previous_decisions.extend(prev_step.get("decisions", []))

        task_tokens = self._token_counter(task)
        step_tokens = self._token_counter(step)
        requirement_tokens = self._token_counter(" ".join(context.get("requirements", [])))
        decision_tokens = self._token_counter(" ".join(previous_decisions))
        candidate_tokens = self._token_counter(candidate_text)
        summary_tokens = self._token_counter(summary_text)

        context_tokens = task_tokens + step_tokens + requirement_tokens + decision_tokens
        important_step_tokens = {
            token
            for token in step_tokens
            if token in self.IMPORTANT_TOKENS or token not in self.GENERIC_STEP_TOKENS
        }
        missing_step_tokens = [
            token for token in important_step_tokens if candidate_tokens[token] == 0
        ]
        novel_tokens = [
            token
            for token in summary_tokens
            if context_tokens[token] == 0 and token not in self.IMPORTANT_TOKENS
        ]

        cosine_step = self._cosine(step_tokens, summary_tokens)
        cosine_task = self._cosine(task_tokens, summary_tokens)
        cosine_requirements = self._cosine(requirement_tokens, summary_tokens)

        return {
            "task_overlap": self._weighted_overlap(task_tokens, candidate_tokens),
            "step_overlap": self._weighted_overlap(step_tokens, candidate_tokens),
            "requirements_overlap": self._weighted_overlap(
                requirement_tokens, candidate_tokens
            ),
            "decision_overlap": self._weighted_overlap(decision_tokens, candidate_tokens),
            "summary_step_overlap": self._weighted_overlap(step_tokens, summary_tokens),
            "summary_task_overlap": self._weighted_overlap(task_tokens, summary_tokens),
            "summary_requirements_overlap": self._weighted_overlap(
                requirement_tokens, summary_tokens
            ),
            "cosine_step": cosine_step,
            "cosine_task": cosine_task,
            "cosine_requirements": cosine_requirements,
            "novel_token_ratio": self._ratio(len(novel_tokens), len(candidate_tokens)),
            "missing_step_ratio": self._ratio(
                len(missing_step_tokens), len(important_step_tokens)
            ),
            "has_previous_decisions": 1.0 if sum(decision_tokens.values()) > 0 else 0.0,
            "candidate_length": float(sum(candidate_tokens.values())),
            "summary_length": float(sum(summary_tokens.values())),
        }

    def _collect_issues(self, features: dict) -> list[str]:
        issues = []

        if (
            features["step_overlap"] < 0.18
            and features["summary_step_overlap"] < 0.2
            and features["cosine_step"] < 0.22
        ):
            issues.append("Candidate output is weakly connected to the current step")
        if (
            features["task_overlap"] < 0.16
            and features["summary_task_overlap"] < 0.18
            and features["cosine_task"] < 0.18
        ):
            issues.append("Candidate output is weakly grounded in the original task")
        if (
            features["requirements_overlap"] < 0.12
            and features["summary_requirements_overlap"] < 0.12
            and features["cosine_requirements"] < 0.18
        ):
            issues.append("Candidate output covers too little of the extracted requirements")
        if features["has_previous_decisions"] and features["decision_overlap"] < 0.08:
            issues.append("Candidate output may ignore earlier implementation decisions")
        if features["novel_token_ratio"] > 0.3:
            issues.append("Candidate output introduces too many tokens outside the known context")
        if features["missing_step_ratio"] > 0.6 and features["cosine_step"] < 0.35:
            issues.append("Candidate output misses too many key tokens from the current step")

        return issues

    def _compute_alignment(self, features: dict) -> float:
        return (
            features["step_overlap"] * 0.3
            + features["summary_step_overlap"] * 0.2
            + features["task_overlap"] * 0.15
            + max(
                features["requirements_overlap"],
                features["summary_requirements_overlap"],
            )
            * 0.15
            + features["decision_overlap"] * 0.1
            + features["cosine_step"] * 0.1
        )

    def _compute_suspicion(self, features: dict, issues: list[str]) -> float:
        suspicion = 0.0

        if features["step_overlap"] < 0.12 and features["cosine_step"] < 0.18:
            suspicion += 0.3
        if (
            features["summary_step_overlap"] < 0.12
            and features["cosine_step"] < 0.18
        ):
            suspicion += 0.15
        if features["task_overlap"] < 0.12 and features["cosine_task"] < 0.14:
            suspicion += 0.15
        if (
            features["requirements_overlap"] < 0.08
            and features["summary_requirements_overlap"] < 0.08
            and features["cosine_requirements"] < 0.14
        ):
            suspicion += 0.1
        if features["has_previous_decisions"] and features["decision_overlap"] < 0.05:
            suspicion += 0.1
        if features["novel_token_ratio"] > 0.4 and features["cosine_step"] < 0.28:
            suspicion += 0.1
        if features["missing_step_ratio"] > 0.7 and features["cosine_step"] < 0.22:
            suspicion += 0.2

        suspicion += min(0.16, 0.03 * len(issues))
        return min(1.0, suspicion)

    def _token_counter(self, text: str) -> Counter:
        tokens = []
        for raw_token in re.findall(r"[a-zA-Z_]{3,}", text.lower()):
            normalized = self._normalize_token(raw_token)
            if normalized and normalized not in self.STOP_WORDS:
                tokens.append(normalized)
        return Counter(tokens)

    def _normalize_token(self, token: str) -> str:
        if token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        return self.SYNONYM_MAP.get(token, token)

    def _weighted_overlap(self, source: Counter, target: Counter) -> float:
        if not source or not target:
            return 0.0

        overlap = 0.0
        source_total = 0.0
        for token, count in source.items():
            token_weight = 2.0 if token in self.IMPORTANT_TOKENS else 1.0
            overlap += min(count, target[token]) * token_weight
            source_total += count * token_weight

        return overlap / source_total if source_total else 0.0

    def _cosine(self, source: Counter, target: Counter) -> float:
        if not source or not target:
            return 0.0

        dot_product = 0.0
        for token, count in source.items():
            dot_product += count * target[token]

        source_norm = math.sqrt(sum(count * count for count in source.values()))
        target_norm = math.sqrt(sum(count * count for count in target.values()))
        if not source_norm or not target_norm:
            return 0.0

        return dot_product / (source_norm * target_norm)

    def _ratio(self, numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0
