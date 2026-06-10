from datetime import datetime, timezone
import hashlib
from typing import Any

from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService


class RealSignalEngineService:
    """Rule-based SMC signal engine driven by MT5 candles and live ticks."""

    symbols = {"EURUSD", "XAUUSD"}
    timeframes = ("M15", "H1", "H4")
    min_rr = 1.5
    tradeable_confidence = 75
    watchlist_confidence = 60
    max_spread = {"EURUSD": 0.0003, "XAUUSD": 1.0}

    def __init__(
        self,
        backfill_service: MT5HistoricalBackfillService | None = None,
        market_data_service: MT5MarketDataService | None = None,
    ) -> None:
        self.backfill_service = backfill_service or MT5HistoricalBackfillService()
        self.market_data_service = market_data_service or MT5MarketDataService()
        self._latest: dict[str, dict[str, Any]] = {}

    def status(self) -> dict[str, Any]:
        return {
            "status": "REAL_SIGNAL_ENGINE_READY",
            "mode": "SMC_MULTI_TIMEFRAME_RULE_ENGINE",
            "symbols": sorted(self.symbols),
            "timeframes": list(self.timeframes),
            "confidence_thresholds": {
                "wait_below": self.watchlist_confidence,
                "watchlist": [self.watchlist_confidence, self.tradeable_confidence - 1],
                "tradeable": self.tradeable_confidence,
            },
            "minimum_risk_reward": self.min_rr,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def latest(self, symbol: str | None = None) -> dict[str, Any]:
        if symbol:
            normalized = self._normalize_symbol(symbol)
            return self._latest.get(normalized) or self.generate_signal(normalized)
        return {
            "status": "READY",
            "signals": [self._latest.get(symbol) or self.generate_signal(symbol) for symbol in sorted(self.symbols)],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def generate_signal(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        if normalized not in self.symbols:
            return self._wait(normalized, ["Unsupported real signal symbol."], "INSUFFICIENT_DATA")

        feed = self._load_feed(normalized)
        if feed["blockers"]:
            signal = self._wait(normalized, feed["blockers"], "INSUFFICIENT_DATA", feed=feed)
            self._latest[normalized] = signal
            return signal

        tick = self.market_data_service.get_symbol_tick(normalized)
        candles = feed["timeframes"]
        h4 = self._timeframe_context(candles["H4"])
        h1 = self._timeframe_context(candles["H1"])
        m15 = self._timeframe_context(candles["M15"])
        direction = self._aligned_direction(h4["bias"], h1["bias"], m15)
        smc = self._smc_components(candles["M15"], direction)
        session = self._session_context()
        spread = self._spread_context(normalized, tick)
        volatility = self._volatility_context(candles["M15"], normalized)
        score = self._score_setup(direction, h4, h1, m15, smc, session, spread, volatility)
        reasons = self._reasons(direction, score, smc, session, spread, volatility)
        trade_plan = self._trade_plan(normalized, direction, tick, candles["M15"], smc) if direction in {"BUY", "SELL"} else {}

        if trade_plan.get("risk_reward") is None or trade_plan.get("risk_reward", 0) < self.min_rr:
            reasons.append("Risk/reward is below the 1.5 minimum or trade plan is incomplete.")

        tradeable = (
            direction in {"BUY", "SELL"}
            and score["confidence"] >= self.tradeable_confidence
            and trade_plan.get("risk_reward", 0) >= self.min_rr
            and spread["acceptable"]
            and session["valid"]
        )
        signal_action = direction if tradeable else "WAIT"
        execution_status = "READY_FOR_PREVIEW" if tradeable else "WAITING"
        risk_status = "APPROVED" if tradeable else ("REJECTED" if score["confidence"] >= self.watchlist_confidence else "NO_SIGNAL")
        if signal_action == "WAIT":
            trade_plan = {}

        signal = {
            "symbol": normalized,
            "signal": signal_action,
            "confidence": score["confidence"] if score["confidence"] >= self.watchlist_confidence else None,
            "reason": self._reason_text(reasons),
            "setup_reason": self._reason_text(reasons),
            "entry": trade_plan.get("entry"),
            "stop_loss": trade_plan.get("stop_loss"),
            "take_profit": trade_plan.get("take_profit"),
            "risk_reward": trade_plan.get("risk_reward"),
            "risk_status": risk_status,
            "execution_status": execution_status,
            "market_structure_state": {
                "higher_timeframe_bias": h4["bias"],
                "intermediate_timeframe_bias": h1["bias"],
                "lower_timeframe_bias": m15["bias"],
                "trend_bias": direction if direction in {"BUY", "SELL"} else "ranging",
                "premium_discount": smc["premium_discount_zone"],
            },
            "strategy_components": {
                "liquidity_sweep": smc["liquidity_sweep"],
                "bos": smc["bos"],
                "choch": smc["choch"],
                "fvg": smc["fvg"],
                "order_block": smc["order_block"],
                "session_valid": session["valid"],
                "bias": direction if direction in {"BUY", "SELL"} else "ranging",
                "session": session["name"],
                "spread_quality": spread["quality"],
                "volatility_quality": volatility["quality"],
            },
            "quality_score": score,
            "approval_audit": self._approval_audit(signal_action, score, smc, trade_plan, session, spread, reasons),
            "candle_source": feed["candle_source"],
            "signal_hash": self._signal_hash(normalized, signal_action, trade_plan, score),
            "data_source": "REAL_SMC_MT5_MULTI_TIMEFRAME",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }
        self._latest[normalized] = signal
        return signal

    def analyze_from_candles(self, symbol: str, timeframes: dict[str, list[dict[str, Any]]], tick: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        original_backfill = self.backfill_service
        original_market = self.market_data_service

        class StaticBackfill:
            def fetch_history(_, requested_symbol: str, timeframe: str, count: int = 500) -> dict[str, Any]:
                candles = timeframes.get(timeframe, [])
                return {
                    "symbol": requested_symbol,
                    "timeframe": timeframe,
                    "candles": candles[-count:],
                    "status": "OK" if candles else "HISTORY_UNAVAILABLE",
                    "validation": {"valid": bool(candles), "stale": False, "gaps_detected": False, "warnings": []},
                }

        class StaticMarket:
            def get_symbol_tick(_, requested_symbol: str) -> dict[str, Any]:
                return tick or {"symbol": requested_symbol, "status": "OK", "bid": 1.0, "ask": 1.0001, "spread": 0.0001, "freshness": "READY"}

        try:
            self.backfill_service = StaticBackfill()  # type: ignore[assignment]
            self.market_data_service = StaticMarket()  # type: ignore[assignment]
            return self.generate_signal(normalized)
        finally:
            self.backfill_service = original_backfill
            self.market_data_service = original_market

    def _load_feed(self, symbol: str) -> dict[str, Any]:
        blockers: list[str] = []
        timeframes: dict[str, list[dict[str, Any]]] = {}
        validation: dict[str, Any] = {}
        candle_source: dict[str, Any] = {
            "symbol": symbol,
            "source": "UNKNOWN",
            "broker_source": "UNKNOWN",
            "account_login": "",
            "server": "",
            "account_type": "",
            "timeframes": {},
        }
        for timeframe in self.timeframes:
            history = self.backfill_service.fetch_history(symbol, timeframe, count=220)
            candles = history.get("candles", [])
            timeframes[timeframe] = candles
            validation[timeframe] = history.get("validation", {})
            if candle_source["source"] == "UNKNOWN":
                candle_source["source"] = history.get("source", "MT5_DEMO")
                candle_source["broker_source"] = history.get("broker_source", history.get("source", "MT5_DEMO"))
                candle_source["account_login"] = history.get("account_login", "")
                candle_source["server"] = history.get("server", "")
                candle_source["account_type"] = history.get("account_type", "")
            candle_source["timeframes"][timeframe] = {
                "timeframe": timeframe,
                "requested_count": history.get("requested_count", 220),
                "returned_count": history.get("returned_count", len(candles)),
                "last_candle_timestamp": candles[-1].get("time") if candles else None,
                "status": history.get("status"),
                "source": history.get("source", candle_source["source"]),
                "broker_source": history.get("broker_source", candle_source["broker_source"]),
            }
            if history.get("status") != "OK" or len(candles) < 30:
                blockers.append(f"{timeframe} history has insufficient real candles.")
        return {"timeframes": timeframes, "validation": validation, "blockers": blockers, "candle_source": candle_source}

    def _timeframe_context(self, candles: list[dict[str, Any]]) -> dict[str, Any]:
        closes = [float(c["close"]) for c in candles if self._valid_candle(c)]
        if len(closes) < 30:
            return {"bias": "ranging", "strength": 0.0}
        fast = sum(closes[-10:]) / 10
        slow = sum(closes[-30:]) / 30
        slope = closes[-1] - closes[-10]
        atr = self._atr(candles[-20:])
        threshold = max(atr * 0.15, closes[-1] * 0.00005)
        if fast > slow and slope > threshold:
            return {"bias": "bullish", "strength": min(1.0, abs(slope) / max(atr, 1e-9))}
        if fast < slow and slope < -threshold:
            return {"bias": "bearish", "strength": min(1.0, abs(slope) / max(atr, 1e-9))}
        return {"bias": "ranging", "strength": 0.35}

    def _aligned_direction(self, h4_bias: str, h1_bias: str, m15: dict[str, Any]) -> str:
        if h4_bias == h1_bias == "bullish" and m15["bias"] in {"bullish", "ranging"}:
            return "BUY"
        if h4_bias == h1_bias == "bearish" and m15["bias"] in {"bearish", "ranging"}:
            return "SELL"
        return "WAIT"

    def _smc_components(self, candles: list[dict[str, Any]], direction: str) -> dict[str, Any]:
        recent = candles[-30:]
        previous = candles[-31:-1]
        last = recent[-1]
        prev_high = max(float(c["high"]) for c in previous[-12:])
        prev_low = min(float(c["low"]) for c in previous[-12:])
        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])
        bullish_sweep = low < prev_low and close > prev_low
        bearish_sweep = high > prev_high and close < prev_high
        bullish_bos = close > prev_high
        bearish_bos = close < prev_low
        bullish_choch = self._choch(candles, "BUY")
        bearish_choch = self._choch(candles, "SELL")
        fvg = self._fvg(candles, direction)
        ob = self._order_block(candles, direction)
        range_high = max(float(c["high"]) for c in recent)
        range_low = min(float(c["low"]) for c in recent)
        midpoint = (range_high + range_low) / 2
        zone = "discount" if close < midpoint else "premium"
        return {
            "liquidity_sweep": bullish_sweep if direction == "BUY" else bearish_sweep if direction == "SELL" else bullish_sweep or bearish_sweep,
            "bos": bullish_bos if direction == "BUY" else bearish_bos if direction == "SELL" else False,
            "choch": bullish_choch if direction == "BUY" else bearish_choch if direction == "SELL" else False,
            "fvg": fvg,
            "order_block": ob is not None,
            "order_block_price": ob,
            "premium_discount_zone": zone,
            "sweep_direction": "bullish" if bullish_sweep else "bearish" if bearish_sweep else "none",
        }

    def _choch(self, candles: list[dict[str, Any]], direction: str) -> bool:
        if len(candles) < 20:
            return False
        prior = candles[-20:-8]
        recent = candles[-8:]
        if direction == "BUY":
            return min(float(c["low"]) for c in recent[:4]) < min(float(c["low"]) for c in prior) and float(recent[-1]["close"]) > max(float(c["high"]) for c in recent[:4])
        return max(float(c["high"]) for c in recent[:4]) > max(float(c["high"]) for c in prior) and float(recent[-1]["close"]) < min(float(c["low"]) for c in recent[:4])

    def _fvg(self, candles: list[dict[str, Any]], direction: str) -> bool:
        for i in range(max(2, len(candles) - 12), len(candles)):
            c0 = candles[i - 2]
            c2 = candles[i]
            if direction == "BUY" and float(c2["low"]) > float(c0["high"]):
                return True
            if direction == "SELL" and float(c2["high"]) < float(c0["low"]):
                return True
        return False

    def _order_block(self, candles: list[dict[str, Any]], direction: str) -> float | None:
        if direction not in {"BUY", "SELL"}:
            return None
        for candle in reversed(candles[-15:-1]):
            open_price = float(candle["open"])
            close = float(candle["close"])
            if direction == "BUY" and close < open_price:
                return float(candle["low"])
            if direction == "SELL" and close > open_price:
                return float(candle["high"])
        return None

    def _session_context(self) -> dict[str, Any]:
        hour = datetime.now(timezone.utc).hour
        if 12 <= hour < 16:
            return {"name": "London/New York overlap", "valid": True, "quality": 1.0}
        if 7 <= hour < 16:
            return {"name": "London", "valid": True, "quality": 0.85}
        if 12 <= hour < 21:
            return {"name": "New York", "valid": True, "quality": 0.85}
        return {"name": "Outside London/New York", "valid": False, "quality": 0.25}

    def _spread_context(self, symbol: str, tick: dict[str, Any]) -> dict[str, Any]:
        spread = self._number(tick.get("spread"))
        max_spread = self.max_spread[symbol]
        acceptable = tick.get("status") == "OK" and spread is not None and spread <= max_spread
        if acceptable and spread <= max_spread * 0.5:
            quality = 1.0
        elif acceptable:
            quality = 0.7
        else:
            quality = 0.0
        return {"spread": spread, "acceptable": acceptable, "quality": quality, "max_spread": max_spread}

    def _volatility_context(self, candles: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
        atr = self._atr(candles[-20:])
        close = float(candles[-1]["close"])
        ratio = atr / close if close else 0
        lower = 0.00005 if symbol == "EURUSD" else 0.0002
        upper = 0.003 if symbol == "EURUSD" else 0.01
        acceptable = lower <= ratio <= upper
        return {"atr": atr, "ratio": ratio, "acceptable": acceptable, "quality": 1.0 if acceptable else 0.35}

    def _score_setup(self, direction: str, h4: dict[str, Any], h1: dict[str, Any], m15: dict[str, Any], smc: dict[str, Any], session: dict[str, Any], spread: dict[str, Any], volatility: dict[str, Any]) -> dict[str, Any]:
        factors = {
            "trend_alignment": 20 if direction in {"BUY", "SELL"} else 0,
            "bos_strength": 15 if smc["bos"] else 0,
            "liquidity_sweep_quality": 15 if smc["liquidity_sweep"] else 0,
            "fvg_quality": 10 if smc["fvg"] else 0,
            "order_block_quality": 10 if smc["order_block"] else 0,
            "session_quality": round(10 * session["quality"], 2),
            "spread_quality": round(10 * spread["quality"], 2),
            "volatility_quality": round(10 * volatility["quality"], 2),
        }
        confidence = int(round(sum(factors.values())))
        if confidence < self.watchlist_confidence:
            rating = "WAIT"
        elif confidence < self.tradeable_confidence:
            rating = "WATCHLIST"
        else:
            rating = "TRADEABLE"
        return {"confidence": min(100, confidence), "rating": rating, "factors": factors}

    def _trade_plan(self, symbol: str, direction: str, tick: dict[str, Any], candles: list[dict[str, Any]], smc: dict[str, Any]) -> dict[str, Any]:
        entry_key = "ask" if direction == "BUY" else "bid"
        entry = self._number(tick.get(entry_key)) or float(candles[-1]["close"])
        atr = self._atr(candles[-20:])
        if direction == "BUY":
            structural_sl = min(float(c["low"]) for c in candles[-10:])
            ob = smc.get("order_block_price")
            stop = min(structural_sl, ob) if isinstance(ob, (int, float)) else structural_sl
            stop_loss = min(stop, entry - atr * 0.8)
            risk = entry - stop_loss
            take_profit = entry + risk * 2.0
        else:
            structural_sl = max(float(c["high"]) for c in candles[-10:])
            ob = smc.get("order_block_price")
            stop = max(structural_sl, ob) if isinstance(ob, (int, float)) else structural_sl
            stop_loss = max(stop, entry + atr * 0.8)
            risk = stop_loss - entry
            take_profit = entry - risk * 2.0
        if risk <= 0:
            return {}
        digits = 2 if symbol == "XAUUSD" else 5
        rr = abs(take_profit - entry) / risk
        return {
            "entry": round(entry, digits),
            "stop_loss": round(stop_loss, digits),
            "take_profit": round(take_profit, digits),
            "risk_reward": round(rr, 2),
        }

    def _reasons(self, direction: str, score: dict[str, Any], smc: dict[str, Any], session: dict[str, Any], spread: dict[str, Any], volatility: dict[str, Any]) -> list[str]:
        reasons = []
        if direction not in {"BUY", "SELL"}:
            reasons.append("M15/H1/H4 timeframe alignment is not confirmed.")
        if score["confidence"] < self.tradeable_confidence:
            reasons.append(f"Setup quality is {score['rating']} with confidence {score['confidence']}; tradeable threshold is 75.")
        if not smc["liquidity_sweep"]:
            reasons.append("Liquidity sweep not confirmed.")
        if not smc["bos"]:
            reasons.append("Break of structure not confirmed.")
        if not smc["fvg"]:
            reasons.append("Fair value gap not confirmed.")
        if not smc["order_block"]:
            reasons.append("Order block not confirmed.")
        if not session["valid"]:
            reasons.append("Current time is outside London/New York trading sessions.")
        if not spread["acceptable"]:
            reasons.append("Spread is not acceptable for preview readiness.")
        if not volatility["acceptable"]:
            reasons.append("Volatility is outside the acceptable range.")
        if not reasons:
            reasons.append(f"{direction} setup is tradeable: aligned trend, SMC confirmation, session, spread, and RR checks passed.")
        return reasons

    def _approval_audit(
        self,
        signal_action: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
        reasons: list[str],
    ) -> dict[str, Any]:
        rr = self._number(trade_plan.get("risk_reward"))
        approved = signal_action in {"BUY", "SELL"}
        return {
            "status": "APPROVED" if approved else ("REJECTED" if score["confidence"] >= self.watchlist_confidence else "WAIT"),
            "final_decision": signal_action,
            "final_approval_reason": self._reason_text(reasons),
            "bos_result": "PASS" if smc["bos"] else "FAIL",
            "choch_result": "PASS" if smc["choch"] else "FAIL",
            "liquidity_sweep_result": "PASS" if smc["liquidity_sweep"] else "FAIL",
            "fvg_result": "PASS" if smc["fvg"] else "FAIL",
            "order_block_result": "PASS" if smc["order_block"] else "FAIL",
            "rr_result": "PASS" if rr is not None and rr >= self.min_rr else "FAIL",
            "rr": rr,
            "confidence_result": "PASS" if score["confidence"] >= self.tradeable_confidence else "FAIL",
            "confidence": score["confidence"],
            "confidence_threshold": self.tradeable_confidence,
            "session_result": "PASS" if session["valid"] else "FAIL",
            "spread_result": "PASS" if spread["acceptable"] else "FAIL",
            "approval_model": "weighted_smc_score",
            "approval_note": "CHOCH and liquidity sweep add confidence but are not mandatory when weighted trend, BOS, FVG, order block, session, spread, volatility, and RR satisfy the approval threshold.",
        }

    def _wait(self, symbol: str, reasons: list[str], risk_status: str = "NO_SIGNAL", feed: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "signal": "WAIT",
            "confidence": None,
            "reason": self._reason_text(reasons),
            "setup_reason": self._reason_text(reasons),
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "risk_status": risk_status,
            "execution_status": "WAITING" if risk_status != "INSUFFICIENT_DATA" else "BLOCKED",
            "market_structure_state": {"trend_bias": "unknown", "higher_timeframe_bias": "unknown", "lower_timeframe_bias": "unknown"},
            "strategy_components": {
                "liquidity_sweep": None,
                "bos": None,
                "choch": None,
                "fvg": None,
                "order_block": None,
                "session_valid": None,
                "bias": "unknown",
                "session": None,
            },
            "quality_score": {"confidence": 0, "rating": "WAIT", "factors": {}},
            "approval_audit": {
                "status": risk_status,
                "final_decision": "WAIT",
                "final_approval_reason": self._reason_text(reasons),
                "confidence_result": "INSUFFICIENT_DATA",
            },
            "candle_source": (feed or {}).get("candle_source", {"symbol": symbol, "timeframes": {}}),
            "data_source": "REAL_SMC_MT5_MULTI_TIMEFRAME",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _atr(self, candles: list[dict[str, Any]]) -> float:
        if len(candles) < 2:
            return 0.0
        ranges = []
        for index in range(1, len(candles)):
            high = float(candles[index]["high"])
            low = float(candles[index]["low"])
            prev_close = float(candles[index - 1]["close"])
            ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        return sum(ranges) / len(ranges)

    def _valid_candle(self, candle: dict[str, Any]) -> bool:
        try:
            return min(float(candle["open"]), float(candle["high"]), float(candle["low"]), float(candle["close"])) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def _reason_text(self, reasons: list[str]) -> str:
        return " ".join(reason for reason in reasons if reason).strip() or "No confirmed setup available."

    def _signal_hash(self, symbol: str, signal: str, plan: dict[str, Any], score: dict[str, Any]) -> str:
        raw = "|".join(str(item) for item in [symbol, signal, plan.get("entry"), plan.get("stop_loss"), plan.get("take_profit"), score.get("confidence")])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _number(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol or "").strip().upper()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
