from pathlib import Path
import re

from backend.system_health.health_models import SafetyScanResult


class SafetyScanner:
    """Scan Python backend source for broker-submission and live-enable tokens."""

    def __init__(self, backend_root: Path | None = None) -> None:
        self.backend_root = backend_root or Path(__file__).resolve().parents[1]
        self._submission_token = "order" + "_send"
        self._live_flag = "live_execution_enabled"
        self._real_flag = "real_trading_enabled"
        self._patterns = [
            (self._submission_token, re.compile(self._submission_token + r"\s*\(")),
            ("mt5." + self._submission_token, re.compile(r"mt5\s*\.\s*" + self._submission_token)),
            (self._live_flag, re.compile(self._live_flag + r"\s*=\s*" + "True")),
            (self._live_flag, re.compile(r"""["']""" + self._live_flag + r"""["']\s*:\s*""" + "true", re.IGNORECASE)),
            (self._real_flag, re.compile(self._real_flag + r"\s*=\s*" + "True")),
            ("broker." + "send" + "_order", re.compile(r"broker\s*\.\s*" + "send" + r"_order\s*\(")),
            ("broker." + "place" + "_order", re.compile(r"broker\s*\.\s*" + "place" + r"_order\s*\(")),
        ]

    def scan(self) -> SafetyScanResult:
        findings: list[str] = []
        unsafe_files: list[str] = []
        for path in self._source_files():
            try:
                contents = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            matched = [label for label, pattern in self._patterns if pattern.search(contents)]
            if matched:
                relative = path.relative_to(self.backend_root).as_posix()
                unsafe_files.append(relative)
                findings.extend(f"{relative}: {pattern}" for pattern in matched)
        order_send_found = any(self._submission_token in finding for finding in findings)
        live_enabled = any(self._live_flag in finding or self._real_flag in finding for finding in findings)
        passed = not findings
        return SafetyScanResult(
            passed=passed,
            forbidden_patterns_found=findings,
            live_execution_enabled=live_enabled,
            order_send_found=order_send_found,
            unsafe_files=sorted(set(unsafe_files)),
            message="Safety boundary scan passed." if passed else "Forbidden live-execution source patterns detected.",
        )

    def _source_files(self):
        for path in self.backend_root.rglob("*.py"):
            if not any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
                yield path
