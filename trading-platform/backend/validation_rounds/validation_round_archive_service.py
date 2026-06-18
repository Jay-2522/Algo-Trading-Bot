from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUNDS_DIR = PROJECT_ROOT / "data" / "validation_rounds"
REASON_STORE_PATH = PROJECT_ROOT / "data" / "reason_panel" / "reason_messages.json"
KNOWN_ROUND_SESSION_IDS = {
    "auto-validation-6dbfe380-22b1-44ea-9fc2-f4b7c25c3de9": 2,
}


class ValidationRoundArchiveService:
    """Persistent round-scoped archive for AUTO validation sessions."""

    def __init__(self, rounds_dir: Path | None = None) -> None:
        self.rounds_dir = rounds_dir or DEFAULT_ROUNDS_DIR
        self.active_path = self.rounds_dir / "active_round.json"
        self.index_path = self.rounds_dir / "rounds_index.json"

    def load_active(self) -> dict[str, Any] | None:
        return self._read_json(self.active_path)

    def start_round(self, session: dict[str, Any], config: dict[str, Any], previous_session: dict[str, Any] | None = None) -> dict[str, Any]:
        self.rounds_dir.mkdir(parents=True, exist_ok=True)
        previous_active = self.load_active()
        if previous_active and previous_active.get("session_id") != session.get("session_id") and previous_active.get("status") != "COMPLETED":
            previous_snapshot = self._read_round(str(previous_active.get("session_id") or "")) or dict(previous_active)
            previous_snapshot["status"] = "ARCHIVED"
            previous_snapshot["archived_reason"] = "NEW_ROUND_STARTED"
            self._write_round(previous_snapshot)
        round_number = KNOWN_ROUND_SESSION_IDS.get(str(session.get("session_id") or ""), self._next_round_number(self._round_number_from_session(session)))
        round_id = str(session.get("session_id") or "")
        started_at = str(session.get("started_at") or session.get("session_start_time") or "")
        snapshot = {
            "round_id": round_id,
            "active_session_id": round_id,
            "session_id": round_id,
            "round_number": round_number,
            "round_label": f"ROUND_{round_number}",
            "status": "ACTIVE",
            "started_at": started_at,
            "ended_at": None,
            "target_trades": int(session.get("target_validation_trades") or session.get("target_closed_trades") or config.get("target_validation_trades") or 30),
            "closed_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "trades": [],
            "bot_decisions": [],
            "rejection_reasons": [],
            "analytics_summary": {},
            "strategy_config": dict(config),
            "session": dict(session),
        }
        self._write_active(snapshot)
        self._write_round(snapshot)
        self._upsert_index(snapshot)
        return snapshot

    def ensure_active_round(self, session: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        active = self.load_active()
        session_id = str(session.get("session_id") or "")
        if active and active.get("session_id") == session_id:
            return active
        if not session_id:
            return {}
        snapshot = {
            "round_id": session_id,
            "active_session_id": session_id,
            "session_id": session_id,
            "round_number": KNOWN_ROUND_SESSION_IDS.get(session_id, self._round_number_from_session(session) or self._next_round_number(None)),
            "round_label": session.get("round_label") or "",
            "status": "ACTIVE" if session.get("status") not in {"COMPLETED", "STOPPED"} else str(session.get("status")),
            "started_at": session.get("started_at") or session.get("session_start_time"),
            "ended_at": session.get("stopped_at"),
            "target_trades": int(session.get("target_validation_trades") or session.get("target_closed_trades") or config.get("target_validation_trades") or 30),
            "closed_trades": int(session.get("current_closed_trades") or 0),
            "wins": int(session.get("wins") or 0),
            "losses": int(session.get("losses") or 0),
            "win_rate": float(session.get("win_rate") or 0.0),
            "net_pnl": float(session.get("net_pnl") or 0.0),
            "max_drawdown": float(session.get("max_drawdown") or 0.0),
            "profit_factor": float(session.get("profit_factor") or 0.0),
            "trades": [],
            "bot_decisions": [],
            "rejection_reasons": [],
            "analytics_summary": {},
            "strategy_config": dict(config),
            "session": dict(session),
        }
        self._write_active(snapshot)
        self._write_round(snapshot)
        self._upsert_index(snapshot)
        return snapshot

    def update_round(self, session: dict[str, Any], config: dict[str, Any], trades: list[dict[str, Any]], events: list[dict[str, Any]], analytics_summary: dict[str, Any] | None = None) -> dict[str, Any]:
        session_id = str(session.get("session_id") or "")
        if not session_id:
            return {}
        snapshot = self._read_round(session_id) or self.ensure_active_round(session, config)
        bot_decisions = self._round_reason_messages(session_id)
        rejection_reasons = [
            str(item.get("rejection_reason") or item.get("reason") or "")
            for item in bot_decisions
            if str(item.get("status") or "").upper() == "REJECTED" and str(item.get("rejection_reason") or item.get("reason") or "")
        ]
        snapshot.update(
            {
                "round_id": session_id,
                "active_session_id": session_id,
                "session_id": session_id,
                "round_label": session.get("round_label") or snapshot.get("round_label") or "",
                "status": "COMPLETED" if session.get("status") == "COMPLETED" else "ACTIVE",
                "started_at": session.get("started_at") or session.get("session_start_time") or snapshot.get("started_at"),
                "ended_at": session.get("stopped_at") if session.get("status") == "COMPLETED" else snapshot.get("ended_at"),
                "target_trades": int(session.get("target_validation_trades") or session.get("target_closed_trades") or snapshot.get("target_trades") or 30),
                "closed_trades": int(session.get("current_closed_trades") or 0),
                "wins": int(session.get("wins") or 0),
                "losses": int(session.get("losses") or 0),
                "win_rate": float(session.get("win_rate") or 0.0),
                "net_pnl": float(session.get("net_pnl") or 0.0),
                "max_drawdown": float(session.get("max_drawdown") or 0.0),
                "profit_factor": float(session.get("profit_factor") or 0.0),
                "trades": list(trades),
                "bot_decisions": bot_decisions,
                "rejection_reasons": rejection_reasons,
                "analytics_summary": analytics_summary or self._analytics_summary(trades, bot_decisions),
                "strategy_config": dict(config),
                "session": dict(session),
                "events": list(events)[-500:],
            }
        )
        self._write_round(snapshot)
        self._write_active(snapshot)
        self._upsert_index(snapshot)
        return snapshot

    def bootstrap_archived_rounds(self, trades: list[dict[str, Any]], active_session_id: str, config: dict[str, Any]) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for trade in trades:
            session_id = str(trade.get("validation_session_id") or trade.get("session_id") or "")
            if not session_id or session_id == active_session_id:
                continue
            grouped.setdefault(session_id, []).append(trade)
        existing = self._read_index()
        existing_sessions = {
            str(item.get("session_id") or "")
            for item in (existing.get("rounds") if isinstance(existing.get("rounds"), list) else [])
            if isinstance(item, dict)
        }
        for session_id, session_trades in grouped.items():
            known_round_number = KNOWN_ROUND_SESSION_IDS.get(session_id)
            existing_round = self._read_round(session_id)
            if existing_round and known_round_number and int(existing_round.get("round_number") or 0) != known_round_number:
                existing_round["round_number"] = known_round_number
                existing_round["round_label"] = f"ROUND_{known_round_number}"
                if isinstance(existing_round.get("session"), dict):
                    existing_round["session"]["round_number"] = known_round_number
                    existing_round["session"]["round_label"] = f"ROUND_{known_round_number}"
                self._write_round(existing_round)
                self._upsert_index(existing_round)
                existing_sessions.add(session_id)
                continue
            if session_id in existing_sessions or existing_round:
                continue
            closed = [trade for trade in session_trades if str(trade.get("status") or "").upper() == "CLOSED"]
            wins = [trade for trade in closed if str(trade.get("result") or "").upper() == "WIN"]
            losses = [trade for trade in closed if str(trade.get("result") or "").upper() == "LOSS"]
            pnl_values = [self._trade_pnl(trade) for trade in closed]
            started_at = min((str(trade.get("opened_at") or trade.get("created_at") or "") for trade in session_trades if str(trade.get("opened_at") or trade.get("created_at") or "")), default="")
            ended_at = max((str(trade.get("closed_at") or trade.get("updated_at") or "") for trade in session_trades if str(trade.get("closed_at") or trade.get("updated_at") or "")), default="")
            round_number = known_round_number or self._next_round_number(None)
            snapshot = {
                "round_id": session_id,
                "active_session_id": session_id,
                "session_id": session_id,
                "round_number": round_number,
                "round_label": f"ROUND_{round_number}",
                "status": "ARCHIVED",
                "started_at": started_at,
                "ended_at": ended_at,
                "target_trades": int(config.get("target_validation_trades") or config.get("target_closed_trades") or 30),
                "closed_trades": len(closed),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round((len(wins) / len(closed)) * 100, 2) if closed else 0.0,
                "net_pnl": round(sum(pnl_values), 2),
                "max_drawdown": self._max_drawdown(pnl_values),
                "profit_factor": self._profit_factor(pnl_values),
                "trades": session_trades,
                "bot_decisions": self._round_reason_messages(session_id),
                "rejection_reasons": [],
                "analytics_summary": self._analytics_summary(session_trades, self._round_reason_messages(session_id)),
                "strategy_config": dict(config),
                "session": {"session_id": session_id, "status": "ARCHIVED", "round_number": round_number, "round_label": f"ROUND_{round_number}"},
            }
            self._write_round(snapshot)
            self._upsert_index(snapshot)

    def complete_round(self, session: dict[str, Any], config: dict[str, Any], trades: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
        snapshot = self.update_round(session, config, trades, events)
        if snapshot:
            snapshot["status"] = "COMPLETED"
            snapshot["ended_at"] = session.get("stopped_at") or snapshot.get("ended_at")
            self._write_round(snapshot)
            self._write_active(snapshot)
            self._upsert_index(snapshot)
        return snapshot

    def _round_number_from_session(self, session: dict[str, Any]) -> int | None:
        value = session.get("round_number")
        if isinstance(value, int) and value > 0:
            return value
        label = str(session.get("round_label") or "")
        if label.upper().startswith("ROUND_"):
            try:
                return int(label.split("_", 1)[1])
            except (ValueError, IndexError):
                return None
        return None

    def _next_round_number(self, fallback: int | None = None) -> int:
        index = self._read_index()
        rounds = index.get("rounds") if isinstance(index.get("rounds"), list) else []
        numbers = [int(item.get("round_number") or 0) for item in rounds if isinstance(item, dict)]
        if numbers:
            return max(numbers) + 1
        return fallback if fallback and fallback > 0 else 1

    def _analytics_summary(self, trades: list[dict[str, Any]], bot_decisions: list[dict[str, Any]]) -> dict[str, Any]:
        rejected = [item for item in bot_decisions if str(item.get("status") or "").upper() == "REJECTED"]
        losses = [trade for trade in trades if str(trade.get("result") or "").upper() == "LOSS"]
        return {
            "trade_count": len(trades),
            "decision_count": len(bot_decisions),
            "rejection_count": len(rejected),
            "loss_count": len(losses),
        }

    def _trade_pnl(self, trade: dict[str, Any]) -> float:
        for key in ("net_pnl", "profit_loss", "realized_pnl", "pnl"):
            try:
                value = float(trade.get(key) or 0)
            except (TypeError, ValueError):
                value = 0.0
            if value:
                return value
        return 0.0

    def _profit_factor(self, pnl_values: list[float]) -> float:
        gross_profit = sum(value for value in pnl_values if value > 0)
        gross_loss = abs(sum(value for value in pnl_values if value < 0))
        if gross_loss > 0:
            return round(gross_profit / gross_loss, 2)
        return round(gross_profit, 2) if gross_profit > 0 else 0.0

    def _max_drawdown(self, pnl_values: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        drawdown = 0.0
        for value in pnl_values:
            equity += value
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        return round(drawdown, 2)

    def _round_reason_messages(self, session_id: str) -> list[dict[str, Any]]:
        messages = self._read_json(REASON_STORE_PATH)
        if not isinstance(messages, list):
            return []
        return [
            item
            for item in messages
            if isinstance(item, dict)
            and str(item.get("validation_session_id") or item.get("session_id") or "") == session_id
            and not self._legacy_strategy_diagnostic(item)
        ]

    def _legacy_strategy_diagnostic(self, item: dict[str, Any]) -> bool:
        text = " ".join(str(item.get(key) or "") for key in ("reason", "rejection_reason", "decision_reason", "final_decision_reason")).lower()
        legacy_confidence = "confidence" in text and ("75" in text or "threshold" in text or "needs" in text)
        hard_session = "outside" in text and ("london" in text or "new york" in text or "ny" in text)
        hard_order_block = "order block" in text and "not confirmed" in text
        return legacy_confidence or hard_session or hard_order_block

    def _read_round(self, session_id: str) -> dict[str, Any] | None:
        if not session_id:
            return None
        return self._read_json(self.rounds_dir / f"round_{self._safe_name(session_id)}.json")

    def _write_round(self, snapshot: dict[str, Any]) -> None:
        session_id = str(snapshot.get("session_id") or snapshot.get("round_id") or "")
        if not session_id:
            return
        self._write_json(self.rounds_dir / f"round_{self._safe_name(session_id)}.json", snapshot)

    def _write_active(self, snapshot: dict[str, Any]) -> None:
        self._write_json(self.active_path, snapshot)

    def _upsert_index(self, snapshot: dict[str, Any]) -> None:
        index = self._read_index()
        rounds = index.get("rounds") if isinstance(index.get("rounds"), list) else []
        session_id = str(snapshot.get("session_id") or "")
        item = {
            "round_number": snapshot.get("round_number"),
            "round_label": snapshot.get("round_label"),
            "session_id": session_id,
            "status": snapshot.get("status"),
            "started_at": snapshot.get("started_at"),
            "ended_at": snapshot.get("ended_at"),
            "closed_trades": snapshot.get("closed_trades", 0),
            "wins": snapshot.get("wins", 0),
            "losses": snapshot.get("losses", 0),
            "net_pnl": snapshot.get("net_pnl", 0.0),
        }
        updated = [entry for entry in rounds if not isinstance(entry, dict) or entry.get("session_id") != session_id]
        updated.append(item)
        updated = self._reconcile_round_index(updated, session_id if snapshot.get("status") == "ACTIVE" else "")
        updated.sort(key=lambda entry: (int(entry.get("round_number") or 9999), str(entry.get("started_at") or "")) if isinstance(entry, dict) else (9999, ""))
        current_index = self._read_index()
        current_active = str(current_index.get("active_session_id") or "")
        active_session_id = session_id if snapshot.get("status") == "ACTIVE" else ("" if current_active == session_id else current_active)
        self._write_json(self.index_path, {"active_session_id": active_session_id, "rounds": updated})

    def _reconcile_round_index(self, rounds: list[Any], active_session_id: str) -> list[dict[str, Any]]:
        normalized = [dict(item) for item in rounds if isinstance(item, dict)]
        used: set[int] = set()

        def priority(item: dict[str, Any]) -> int:
            session_id = str(item.get("session_id") or "")
            if session_id == active_session_id:
                return 0
            if session_id in KNOWN_ROUND_SESSION_IDS:
                return 1
            return 2

        for item in sorted(normalized, key=priority):
            session_id = str(item.get("session_id") or "")
            known = KNOWN_ROUND_SESSION_IDS.get(session_id)
            if known:
                item["round_number"] = known
                item["round_label"] = f"ROUND_{known}"
            number = int(item.get("round_number") or 0)
            if number <= 0:
                item["round_number"] = None
                item["round_label"] = item.get("round_label") or "ARCHIVED_ATTEMPT"
                continue
            if number in used:
                item["round_number"] = None
                item["round_label"] = "ARCHIVED_ATTEMPT"
                self._rewrite_round_metadata(session_id, None, "ARCHIVED_ATTEMPT")
                continue
            used.add(number)
            self._rewrite_round_metadata(session_id, number, f"ROUND_{number}")
        return normalized

    def _rewrite_round_metadata(self, session_id: str, round_number: int | None, round_label: str) -> None:
        snapshot = self._read_round(session_id)
        if not snapshot:
            return
        snapshot["round_number"] = round_number
        snapshot["round_label"] = round_label
        if isinstance(snapshot.get("session"), dict):
            snapshot["session"]["round_number"] = round_number
            snapshot["session"]["round_label"] = round_label
        self._write_round(snapshot)

    def _read_index(self) -> dict[str, Any]:
        data = self._read_json(self.index_path)
        return data if isinstance(data, dict) else {"active_session_id": "", "rounds": []}

    def _read_json(self, path: Path) -> Any:
        try:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")

    def _safe_name(self, value: str) -> str:
        return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
