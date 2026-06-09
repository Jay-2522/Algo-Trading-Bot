from datetime import datetime
from typing import Any

from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


class TradeOutcomeIntelligenceService:
    """Post-trade attribution and performance metrics from closed demo trades."""

    def __init__(self, journal: PersistentTradeJournalService | None = None) -> None:
        self.journal = journal or PersistentTradeJournalService()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "environment": "DEMO",
            "data_source": "persistent_trade_journal_closed_trades",
            **self._safety_flags(),
        }

    def get_latest(self) -> dict[str, Any]:
        trades = self.get_trades()
        return trades[0] if trades else self._empty("No closed demo trades available.")

    def get_trades(self) -> list[dict[str, Any]]:
        closed = self.journal.get_closed_trades()
        return [self._analyze_trade(trade) for trade in closed]

    def get_symbol_performance(self) -> list[dict[str, Any]]:
        return self._aggregate(self.get_trades(), "symbol")

    def get_side_performance(self) -> list[dict[str, Any]]:
        return self._aggregate(self.get_trades(), "side")

    def get_session_performance(self) -> list[dict[str, Any]]:
        return self._aggregate(self.get_trades(), "market_session")

    def get_summary(self) -> dict[str, Any]:
        trades = self.get_trades()
        symbols = self.get_symbol_performance()
        attribution_counts: dict[str, int] = {}
        for trade in trades:
            reason = trade["outcome_attribution"]
            attribution_counts[reason] = attribution_counts.get(reason, 0) + 1
        return {
            "status": "READY",
            "environment": "DEMO",
            "total_closed_trades": len(trades),
            "wins": len([trade for trade in trades if trade["result"] == "WIN"]),
            "losses": len([trade for trade in trades if trade["result"] == "LOSS"]),
            "breakeven": len([trade for trade in trades if trade["result"] == "BREAKEVEN"]),
            "win_rate": self._win_rate(trades),
            "net_pnl": self._sum(trades, "realized_pnl"),
            "avg_pnl": self._avg([trade["realized_pnl"] for trade in trades]),
            "avg_rr": self._avg([trade["realized_rr"] for trade in trades if trade["realized_rr"] is not None]),
            "best_trade": self._extreme_trade(trades, best=True),
            "worst_trade": self._extreme_trade(trades, best=False),
            "best_symbol": self._extreme_group(symbols, best=True),
            "worst_symbol": self._extreme_group(symbols, best=False),
            "outcome_attribution": attribution_counts,
            "empty_state": len(trades) == 0,
            "message": "No closed demo trades available." if not trades else "Outcome intelligence derived from closed demo trades.",
            **self._safety_flags(),
        }

    def _analyze_trade(self, trade: dict[str, Any]) -> dict[str, Any]:
        result = str(trade.get("result") or self._result_from_pnl(self._pnl(trade))).upper()
        risk_amount = self._risk_amount(trade)
        reward_amount = self._reward_amount(trade)
        pnl = self._pnl(trade)
        realized_rr = round(pnl / risk_amount, 2) if risk_amount else None
        return {
            "trade_id": trade.get("trade_id"),
            "mt5_ticket": trade.get("mt5_ticket"),
            "result": result,
            "realized_pnl": pnl,
            "risk_amount": risk_amount,
            "reward_amount": reward_amount,
            "realized_rr": realized_rr,
            "duration_minutes": self._number(trade.get("duration_minutes")),
            "entry_timestamp": trade.get("opened_at") or trade.get("created_at"),
            "exit_timestamp": trade.get("closed_at"),
            "market_session": self._market_session(trade.get("opened_at") or trade.get("created_at")),
            "symbol": str(trade.get("symbol") or "").upper(),
            "side": str(trade.get("side") or "").upper(),
            "outcome_attribution": self._attribution(trade, result, pnl),
            "exit_reason": str(trade.get("exit_reason") or "UNKNOWN").upper(),
            **self._safety_flags(),
        }

    def _aggregate(self, trades: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        groups = sorted({str(trade.get(key) or "UNKNOWN").upper() for trade in trades})
        return [self._group_summary(group, [trade for trade in trades if str(trade.get(key) or "UNKNOWN").upper() == group], key) for group in groups]

    def _group_summary(self, group: str, trades: list[dict[str, Any]], key: str) -> dict[str, Any]:
        pnl_values = [trade["realized_pnl"] for trade in trades]
        rr_values = [trade["realized_rr"] for trade in trades if trade["realized_rr"] is not None]
        return {
            key: group,
            "total_trades": len(trades),
            "wins": len([trade for trade in trades if trade["result"] == "WIN"]),
            "losses": len([trade for trade in trades if trade["result"] == "LOSS"]),
            "win_rate": self._win_rate(trades),
            "net_pnl": round(sum(pnl_values), 2) if pnl_values else 0.0,
            "avg_pnl": self._avg(pnl_values),
            "avg_rr": self._avg(rr_values),
            **self._safety_flags(),
        }

    def _attribution(self, trade: dict[str, Any], result: str, pnl: float) -> str:
        exit_reason = str(trade.get("exit_reason") or "").upper()
        if result == "WIN":
            if exit_reason == "TAKE_PROFIT":
                return "TP reached"
            if exit_reason == "MANUAL":
                return "manual profitable close"
            return "favorable move"
        if result == "LOSS":
            if exit_reason == "STOP_LOSS":
                return "SL reached"
            if exit_reason == "MANUAL":
                return "manual loss close"
            return "adverse move"
        if abs(pnl) <= 0.01:
            return "minimal pnl"
        return "manual breakeven exit"

    def _risk_amount(self, trade: dict[str, Any]) -> float:
        entry = self._number(trade.get("entry_price"))
        stop = self._number(trade.get("stop_loss"))
        lot = self._number(trade.get("lot"))
        if entry is None or stop is None or lot is None:
            return 0.0
        return round(abs(entry - stop) * lot, 6)

    def _reward_amount(self, trade: dict[str, Any]) -> float:
        entry = self._number(trade.get("entry_price"))
        target = self._number(trade.get("take_profit"))
        lot = self._number(trade.get("lot"))
        if entry is None or target is None or lot is None:
            return 0.0
        return round(abs(target - entry) * lot, 6)

    def _pnl(self, trade: dict[str, Any]) -> float:
        return self._number(trade.get("net_pnl") if trade.get("net_pnl") is not None else trade.get("profit_loss")) or 0.0

    def _market_session(self, timestamp: Any) -> str:
        try:
            hour = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).hour
        except (TypeError, ValueError):
            return "UNKNOWN"
        if 7 <= hour < 12:
            return "LONDON"
        if 12 <= hour < 21:
            return "NEW_YORK"
        return "ASIA"

    def _result_from_pnl(self, pnl: float) -> str:
        if pnl > 0:
            return "WIN"
        if pnl < 0:
            return "LOSS"
        return "BREAKEVEN"

    def _win_rate(self, trades: list[dict[str, Any]]) -> float:
        return round((len([trade for trade in trades if trade["result"] == "WIN"]) / len(trades)) * 100, 2) if trades else 0.0

    def _sum(self, trades: list[dict[str, Any]], key: str) -> float:
        return round(sum(float(trade.get(key) or 0.0) for trade in trades), 2) if trades else 0.0

    def _avg(self, values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    def _extreme_trade(self, trades: list[dict[str, Any]], best: bool) -> dict[str, Any] | None:
        if not trades:
            return None
        return sorted(trades, key=lambda trade: trade["realized_pnl"], reverse=best)[0]

    def _extreme_group(self, groups: list[dict[str, Any]], best: bool) -> str | None:
        if not groups:
            return None
        key = next((item for item in groups[0].keys() if item in {"symbol", "side", "market_session"}), "")
        return str(sorted(groups, key=lambda group: float(group.get("net_pnl") or 0.0), reverse=best)[0].get(key))

    def _number(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _empty(self, message: str) -> dict[str, Any]:
        return {
            "status": "EMPTY",
            "environment": "DEMO",
            "message": message,
            **self._safety_flags(),
        }

    def _safety_flags(self) -> dict[str, bool]:
        return {
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "mt5_order_send_used": False,
        }
