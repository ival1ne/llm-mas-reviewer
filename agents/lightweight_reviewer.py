import re
from collections import Counter


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

    def review(self, task: str, step: str, context: dict, candidate_output: dict):
        graph = self._build_graph(task, step, context, candidate_output)
        score = self._score_graph(graph)
        issues = self._collect_issues(graph)

        if score >= 0.7 and not issues:
            recommendation = "continue"
        elif score >= 0.45:
            recommendation = "revise"
        else:
            recommendation = "regenerate"

        return {
            "reviewer_type": "lightweight",
            "aligned": score >= 0.55 and not issues,
            "score": round(score, 3),
            "issues": issues,
            "recommendation": recommendation,
            "graph": {
                "nodes": list(graph["nodes"].keys()),
                "edges": graph["edges"],
            },
        }

    def _build_graph(
        self, task: str, step: str, context: dict, candidate_output: dict
    ) -> dict:
        previous_decisions = []
        for prev_step in context.get("steps", []):
            previous_decisions.extend(prev_step.get("decisions", []))

        candidate_text = " ".join(
            [
                candidate_output.get("summary", ""),
                candidate_output.get("code", ""),
                " ".join(candidate_output.get("decisions", [])),
                " ".join(candidate_output.get("artifacts", [])),
            ]
        )

        nodes = {
            "task": self._token_counter(task),
            "step": self._token_counter(step),
            "requirements": self._token_counter(" ".join(context.get("requirements", []))),
            "previous_decisions": self._token_counter(" ".join(previous_decisions)),
            "candidate": self._token_counter(candidate_text),
        }

        edges = []
        for source, target in (
            ("task", "candidate"),
            ("step", "candidate"),
            ("requirements", "candidate"),
            ("previous_decisions", "candidate"),
        ):
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "weight": round(
                        self._overlap_ratio(nodes[source], nodes[target]),
                        3,
                    ),
                }
            )

        return {"nodes": nodes, "edges": edges}

    def _score_graph(self, graph: dict) -> float:
        weights = {edge["source"]: edge["weight"] for edge in graph["edges"]}
        return (
            weights.get("task", 0.0) * 0.3
            + weights.get("step", 0.0) * 0.4
            + weights.get("requirements", 0.0) * 0.2
            + weights.get("previous_decisions", 0.0) * 0.1
        )

    def _collect_issues(self, graph: dict) -> list[str]:
        weights = {edge["source"]: edge["weight"] for edge in graph["edges"]}
        issues = []

        if weights.get("step", 0.0) < 0.2:
            issues.append("Candidate output weakly matches the current step")
        if weights.get("task", 0.0) < 0.15:
            issues.append("Candidate output appears weakly grounded in the original task")
        if graph["nodes"]["requirements"] and weights.get("requirements", 0.0) < 0.15:
            issues.append("Candidate output does not sufficiently cover extracted requirements")

        return issues

    def _token_counter(self, text: str) -> Counter:
        tokens = [
            token
            for token in re.findall(r"[a-zA-Z_]{3,}", text.lower())
            if token not in self.STOP_WORDS
        ]
        return Counter(tokens)

    def _overlap_ratio(self, source: Counter, target: Counter) -> float:
        if not source or not target:
            return 0.0

        overlap = sum(min(count, target[token]) for token, count in source.items())
        source_total = sum(source.values())
        return overlap / source_total if source_total else 0.0
