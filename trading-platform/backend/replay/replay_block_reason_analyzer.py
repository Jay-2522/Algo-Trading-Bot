from collections import Counter
from typing import Any

from backend.replay.replay_calibration_models import ReplayBlockReasonMetrics
from backend.replay.replay_models import ReplayStepResult


class ReplayBlockReasonAnalyzer:
    """Classify why replay decisions were blocked or downgraded."""

    BLOCK_ACTIONS = {"AVOID", "NO_TRADE", "BLOCKED"}
    GATE_KEYWORDS = {
        "NEWS": ("news", "blackout", "event risk"),
        "SESSION": ("session", "killzone", "timing", "liquidity window"),
        "CONFLUENCE": ("confluence", "conflict", "alignment conflict", "directional conflict"),
        "SETUP_VALIDATION": ("validation", "weak setup", "setup", "confirmation", "no high-quality"),
        "RISK": ("risk", "drawdown", "rr", "invalidation", "target", "geometry"),
        "ENTRY_GEOMETRY": ("entry zone", "entry", "missing entry", "undefined invalidation", "undefined target"),
        "NO_TRADE": ("no_trade", "no trade", "no valid setup", "no setup"),
    }

    def analyze_block_reasons(self, step_results: list[ReplayStepResult]) -> ReplayBlockReasonMetrics:
        if not step_results:
            return ReplayBlockReasonMetrics(
                total_blocked=0,
                block_rate=0.0,
                common_reasons=["No replay steps available."],
                gate_counts={},
                most_restrictive_gate="NONE",
            )

        blocked_steps = [step for step in step_results if self._is_blocked(step)]
        gate_counts: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        for step in blocked_steps:
            text = self._evidence_text(step)
            matched = False
            for gate, keywords in self.GATE_KEYWORDS.items():
                if any(keyword in text for keyword in keywords):
                    gate_counts[gate] += 1
                    reasons[self._reason_for_gate(gate)] += 1
                    matched = True
            if not matched:
                action = str(step.simulation_decision.get("action", "NO_TRADE") or "NO_TRADE")
                gate = "NO_TRADE" if action == "NO_TRADE" else "SETUP_VALIDATION"
                gate_counts[gate] += 1
                reasons[self._reason_for_gate(gate)] += 1

        most_restrictive = gate_counts.most_common(1)[0][0] if gate_counts else "NONE"
        return ReplayBlockReasonMetrics(
            total_blocked=len(blocked_steps),
            block_rate=round((len(blocked_steps) / len(step_results)) * 100.0, 2),
            common_reasons=[reason for reason, _ in reasons.most_common(5)] or ["No blocking reasons detected."],
            gate_counts=dict(gate_counts),
            most_restrictive_gate=most_restrictive,
        )

    def _is_blocked(self, step: ReplayStepResult) -> bool:
        action = str(step.simulation_decision.get("action", "NO_TRADE") or "NO_TRADE")
        readiness = str(step.simulation_decision.get("readiness", "") or "")
        event_type = str(step.event_type or "")
        return action in self.BLOCK_ACTIONS or readiness in {"BLOCKED", "NO_VALID_SETUP"} or event_type == "BLOCKED"

    def _evidence_text(self, step: ReplayStepResult) -> str:
        evidence: list[Any] = [step.simulation_decision, step.institutional_state, step.paper_trade_state, step.notes]
        return self._flatten_text(evidence).lower().replace("-", "_")

    def _flatten_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            return " ".join(f"{key} {self._flatten_text(item)}" for key, item in value.items())
        if isinstance(value, (list, tuple, set)):
            return " ".join(self._flatten_text(item) for item in value)
        return str(value)

    def _reason_for_gate(self, gate: str) -> str:
        reasons = {
            "NEWS": "News or blackout protection blocked replay simulation.",
            "SESSION": "Session or killzone timing blocked replay simulation.",
            "CONFLUENCE": "Directional confluence conflict blocked replay simulation.",
            "SETUP_VALIDATION": "Setup validation did not meet institutional quality.",
            "RISK": "Risk or reward-to-risk gate blocked replay simulation.",
            "ENTRY_GEOMETRY": "Entry, invalidation, or target geometry was incomplete.",
            "NO_TRADE": "Replay step had no valid institutional setup.",
        }
        return reasons.get(gate, "Replay step was blocked by an unspecified gate.")
