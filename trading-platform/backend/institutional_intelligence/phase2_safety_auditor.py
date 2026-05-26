from pathlib import Path
import re

from backend.institutional_intelligence.phase2_completion_models import Phase2SafetyAudit


class Phase2SafetyAuditor:
    """Inspect backend Python sources for prohibited trade-enabling signatures."""

    def __init__(self, backend_root: Path | None = None) -> None:
        self.backend_root = backend_root or Path(__file__).resolve().parents[1]
        submission = "order" + "_send"
        live_flag = "live_execution" + "_enabled"
        real_flag = "real_trading" + "_enabled"
        activation = "enable" + "_live" + "_trading"
        self._submission = submission
        self._patterns = [
            (submission + " call", re.compile(submission + r"\s*\(")),
            ("mt5 submission call", re.compile(r"mt5\s*\.\s*" + submission)),
            ("live execution enabled", re.compile(live_flag + r"\s*=\s*" + "True")),
            ("real trading enabled", re.compile(real_flag + r"\s*=\s*" + "True")),
            ("live activation", re.compile(activation + r"\s*\(")),
        ]

    def run_safety_audit(self) -> Phase2SafetyAudit:
        findings: list[str] = []
        for path in self._source_files():
            try:
                contents = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for label, pattern in self._patterns:
                if pattern.search(contents):
                    relative = path.relative_to(self.backend_root).as_posix()
                    findings.append(f"{relative}: {label}")
        submission_found = any("submission" in finding or self._submission in finding for finding in findings)
        live_enabled = any("enabled" in finding or "activation" in finding for finding in findings)
        passed = not findings
        return Phase2SafetyAudit(
            passed=passed,
            simulation_only=passed,
            live_execution_enabled=live_enabled,
            order_send_found=submission_found,
            unsafe_patterns=sorted(set(findings)),
            message=(
                "Phase 2 safety audit passed in simulation-only mode."
                if passed
                else "Phase 2 safety audit found prohibited backend source patterns."
            ),
        )

    def _source_files(self):
        for path in self.backend_root.rglob("*.py"):
            if not any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
                yield path
