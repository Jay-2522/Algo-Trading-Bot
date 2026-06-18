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
    auto_validation_confidence = 65
    demo_collection_confidence = 55
    demo_collection_min_rr = 2.0
    history_preload_candles = 300
    history_required_candles = 300

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
            "strategy_profiles": {
                "PRODUCTION": {
                    "min_confidence": self.tradeable_confidence,
                    "bos_contributes_to_confidence": True,
                    "liquidity_sweep_contributes_to_confidence": True,
                    "unchanged": True,
                },
                "AUTO_VALIDATION": {
                    "min_confidence": self.auto_validation_confidence,
                    "bos_mandatory": False,
                    "liquidity_sweep_mandatory": False,
                    "requires": ["BUY_OR_SELL", "FVG", "ORDER_BLOCK", "SESSION_VALID", "SL_TP_VALID", "RR_1_5", "SPREAD_ACCEPTABLE_OR_STALE_WITHIN_GRACE"],
                },
                "DEMO_COLLECTION": {
                    "min_confidence": None,
                    "min_rr": self.demo_collection_min_rr,
                    "confirmation_score_required": 5,
                    "strong_confirmation_required": 2,
                    "confirmation_pool": ["TREND_ALIGNMENT", "LIQUIDITY_SWEEP", "BOS", "FVG_IMBALANCE", "PULLBACK_RETEST", "MOMENTUM_DISPLACEMENT", "ATR_VOLATILITY", "SPREAD_CLEAN", "RR_2_0", "SESSION_BONUS"],
                    "bos_mandatory": False,
                    "liquidity_sweep_mandatory": False,
                    "fvg_mandatory": False,
                    "order_block_mandatory": False,
                    "session_filter": "ADVISORY_BONUS_ONLY",
                    "requires": ["H4_HISTORY", "M15_HISTORY", "RR_2_0", "SPREAD_ACCEPTABLE", "RISK_APPROVED", "DIRECTION_BIAS_MATCH", "EDGE_SCORE_THRESHOLD"],
                    "history_required_candles": self.history_required_candles,
                },
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

    def debug_signal(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        if normalized not in self.symbols:
            return {
                "symbol": normalized,
                "status": "UNSUPPORTED_SYMBOL",
                "reason": "Unsupported real signal symbol.",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "timestamp": self._timestamp(),
            }

        feed = self._load_feed(normalized)
        candle_counts = {timeframe: len(feed["timeframes"].get(timeframe, [])) for timeframe in self.timeframes}
        if feed["blockers"]:
            signal = self._wait(normalized, feed["blockers"], "INSUFFICIENT_DATA", feed=feed)
            return {
                "symbol": normalized,
                "status": "INSUFFICIENT_DATA",
                "signal": signal,
                "exact_reason_buy_not_generated": self._reason_text(feed["blockers"]),
                "exact_reason_sell_not_generated": self._reason_text(feed["blockers"]),
                "candles_analyzed": self._candle_counts(candle_counts),
                "market_regime": "unknown",
                "raw_trend_direction": {"M15": "unknown", "H1": "unknown", "H4": "unknown"},
                "confidence_components": self._empty_debug_components(),
                "final_confidence_calculation": {"formula": "No confidence calculation because candle feed is insufficient.", "final_confidence": 0},
                "diagnostics_only": True,
                "strategy_logic_changed": False,
                "thresholds_changed": False,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "timestamp": self._timestamp(),
            }

        tick = self.market_data_service.get_symbol_tick(normalized)
        candles = feed["timeframes"]
        contexts = {
            "H4": self._timeframe_context(candles["H4"]),
            "H1": self._timeframe_context(candles["H1"]),
            "M15": self._timeframe_context(candles["M15"]),
        }
        direction = self._aligned_direction(contexts["H4"]["bias"], contexts["H1"]["bias"], contexts["M15"])
        smc = self._smc_components(candles["M15"], direction)
        session = self._session_context()
        spread = self._spread_context(normalized, tick)
        volatility = self._volatility_context(candles["M15"], normalized)
        score = self._score_setup(direction, contexts["H4"], contexts["H1"], contexts["M15"], smc, session, spread, volatility)
        trade_plan = self._trade_plan(normalized, direction, tick, candles["M15"], smc) if direction in {"BUY", "SELL"} else {}
        reasons = self._reasons(direction, score, smc, session, spread, volatility)
        if trade_plan.get("risk_reward") is None or trade_plan.get("risk_reward", 0) < self.min_rr:
            reasons.append("Risk/reward is below the 1.5 minimum or trade plan is incomplete.")
        missing_requirements = self._missing_requirements(direction, score, smc, trade_plan, session, spread)
        signal = self.generate_signal(normalized)
        confidence_components = self._debug_confidence_components(score, smc, session, spread, volatility, trade_plan)
        final_calculation = self._debug_confidence_calculation(confidence_components, score)
        direction_reasons = self._direction_rejection_reasons(direction, signal, reasons, missing_requirements)

        return {
            "symbol": normalized,
            "status": "READY",
            "signal": signal,
            "candles_analyzed": self._candle_counts(candle_counts),
            "market_regime": self._market_regime(contexts),
            "raw_trend_direction": {
                "M15": contexts["M15"]["bias"],
                "H1": contexts["H1"]["bias"],
                "H4": contexts["H4"]["bias"],
            },
            "raw_trend_strength": {
                "M15": contexts["M15"]["strength"],
                "H1": contexts["H1"]["strength"],
                "H4": contexts["H4"]["strength"],
            },
            "aligned_direction": direction,
            "smc_components": smc,
            "session_context": session,
            "spread_context": spread,
            "volatility_context": volatility,
            "trade_plan_before_wait_reset": trade_plan,
            "confidence_components": confidence_components,
            "final_confidence_calculation": final_calculation,
            "missing_requirements": missing_requirements,
            "exact_reason_buy_not_generated": direction_reasons["BUY"],
            "exact_reason_sell_not_generated": direction_reasons["SELL"],
            "diagnostic_summary": self._reason_text(reasons),
            "thresholds": {
                "tradeable_confidence": self.tradeable_confidence,
                "watchlist_confidence": self.watchlist_confidence,
                "minimum_risk_reward": self.min_rr,
                "max_spread": self.max_spread[normalized],
            },
            "diagnostics_only": True,
            "strategy_logic_changed": False,
            "thresholds_changed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def generate_signal(self, symbol: str, strategy_profile: str = "PRODUCTION") -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        profile = self._strategy_profile(strategy_profile)
        if normalized not in self.symbols:
            return self._wait(normalized, ["Unsupported real signal symbol."], "INSUFFICIENT_DATA")

        feed = self._load_feed(normalized)
        if feed["blockers"]:
            signal = self._wait(normalized, feed["blockers"], "INSUFFICIENT_DATA", feed=feed)
            signal["strategy_profile"] = profile
            if profile == "DEMO_COLLECTION":
                round3_audit = self._round3_history_audit(normalized, feed)
                signal["round3_diagnostics"] = round3_audit
                signal["approval_audit"] = {**signal.get("approval_audit", {}), **round3_audit}
                signal.update(round3_audit)
                signal["reason"] = round3_audit["final_decision_reason"]
                signal["setup_reason"] = round3_audit["final_decision_reason"]
                signal["what_needs_to_happen_next"] = round3_audit["final_decision_reason"]
                signal["rejection_reason"] = round3_audit["final_decision_reason"]
            self._latest[normalized] = signal
            return signal

        tick = self.market_data_service.get_symbol_tick(normalized)
        candles = feed["timeframes"]
        h4 = self._timeframe_context(candles["H4"])
        h1 = self._timeframe_context(candles["H1"])
        m15 = self._timeframe_context(candles["M15"])
        direction = self._aligned_direction(h4["bias"], h1["bias"], m15)
        if profile == "DEMO_COLLECTION" and direction not in {"BUY", "SELL"}:
            direction = self._demo_collection_direction(h4, h1, m15)
        smc = self._smc_components(candles["M15"], direction)
        session = self._session_context()
        spread = self._spread_context(normalized, tick)
        volatility = self._volatility_context(candles["M15"], normalized)
        score = self._score_setup(direction, h4, h1, m15, smc, session, spread, volatility)
        reasons = self._reasons(direction, score, smc, session, spread, volatility)
        trade_plan = self._trade_plan(normalized, direction, tick, candles["M15"], smc) if direction in {"BUY", "SELL"} else {}
        if profile == "DEMO_COLLECTION":
            trade_plan = self._demo_collection_trade_plan(normalized, direction, tick, candles["M15"], trade_plan)

        profile_min_rr = self.demo_collection_min_rr if profile == "DEMO_COLLECTION" else self.min_rr
        if trade_plan.get("risk_reward") is None or trade_plan.get("risk_reward", 0) < profile_min_rr:
            reasons.append(f"Risk/reward is below the {profile_min_rr:.1f} minimum or trade plan is incomplete.")

        production_tradeable = (
            direction in {"BUY", "SELL"}
            and score["confidence"] >= self.tradeable_confidence
            and trade_plan.get("risk_reward", 0) >= self.min_rr
            and spread["acceptable"]
            and session["valid"]
        )
        auto_tradeable = self._auto_validation_tradeable(direction, score, smc, trade_plan, session, spread)
        round3_audit = self._round3_rule_audit(normalized, feed, direction, smc, session, trade_plan, score, spread)
        demo_collection_tradeable = self._demo_collection_tradeable(direction, score, smc, trade_plan, session, spread, round3_audit)
        tradeable = demo_collection_tradeable if profile == "DEMO_COLLECTION" else auto_tradeable if profile == "AUTO_VALIDATION" else production_tradeable
        signal_action = direction if tradeable else "WAIT"
        execution_status = "READY_FOR_PREVIEW" if tradeable else "WAITING"
        profile_confidence = self._profile_confidence(profile)
        risk_status = "APPROVED" if tradeable else ("REJECTED" if score["confidence"] >= profile_confidence else "NO_SIGNAL")
        if profile == "DEMO_COLLECTION":
            missing_requirements = self._demo_collection_missing_requirements(direction, score, smc, trade_plan, session, spread)
        elif profile == "AUTO_VALIDATION":
            missing_requirements = self._auto_validation_missing_requirements(direction, score, smc, trade_plan, session, spread)
        else:
            missing_requirements = self._missing_requirements(direction, score, smc, trade_plan, session, spread)
        if profile == "DEMO_COLLECTION" and not tradeable:
            hard_codes = {"SPREAD_TOO_HIGH", "SL_TP_INVALID", "RR_MISSING", "RR_LOW", "DIRECTION_BIAS_MISMATCH"}
            risk_status = "REJECTED" if any(item.get("code") in hard_codes for item in missing_requirements) else "NO_SIGNAL"
        if signal_action == "WAIT":
            trade_plan = {}
        status_level = self._status_level(signal_action, score, missing_requirements) if profile == "PRODUCTION" else self._profile_status_level(signal_action, score, missing_requirements, profile_confidence)
        profile_reasons = self._profile_reasons(profile, reasons, missing_requirements)
        rejection_reason = "" if signal_action in {"BUY", "SELL"} else self._reason_text(profile_reasons)
        validator_diagnostics = self._validator_diagnostics(normalized, feed, execution_status, rejection_reason)

        signal = {
            "symbol": normalized,
            "signal": signal_action,
            "status_level": status_level,
            "confidence": score["confidence"] if score["confidence"] >= min(self.watchlist_confidence, profile_confidence) else None,
            "reason": self._reason_text(profile_reasons),
            "what_needs_to_happen_next": self._next_steps(missing_requirements, score, self.auto_validation_confidence if profile == "AUTO_VALIDATION" else self.tradeable_confidence),
            "missing_requirements": missing_requirements,
            "setup_reason": self._reason_text(profile_reasons),
            "entry": trade_plan.get("entry"),
            "stop_loss": trade_plan.get("stop_loss"),
            "take_profit": trade_plan.get("take_profit"),
            "risk_reward": trade_plan.get("risk_reward"),
            "sl_tp_source": trade_plan.get("sl_tp_source"),
            "demo_risk_model": trade_plan.get("demo_risk_model"),
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
            "approval_audit": self._profile_approval_audit(profile, signal_action, score, smc, trade_plan, session, spread, profile_reasons, missing_requirements),
            "round3_diagnostics": round3_audit if profile == "DEMO_COLLECTION" else {},
            "candle_source": feed["candle_source"],
            "signal_hash": self._signal_hash(normalized, signal_action, trade_plan, score),
            "data_source": "REAL_SMC_MT5_MULTI_TIMEFRAME",
            **validator_diagnostics,
            **(round3_audit if profile == "DEMO_COLLECTION" else {}),
            "strategy_profile": profile,
            "production_rules_unchanged": profile == "PRODUCTION",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }
        if profile == "DEMO_COLLECTION":
            signal["reason"] = round3_audit["final_decision_reason"]
            signal["setup_reason"] = round3_audit["final_decision_reason"]
            signal["what_needs_to_happen_next"] = (
                "All Round 3 entry rules are currently satisfied."
                if not round3_audit.get("failed_rules")
                else round3_audit["final_decision_reason"]
            )
            signal["approval_audit"] = {**signal.get("approval_audit", {}), **round3_audit}
        self._latest[normalized] = signal
        return signal

    def _strategy_profile(self, strategy_profile: str) -> str:
        profile = str(strategy_profile or "").upper()
        if profile in {"AUTO_VALIDATION", "DEMO_COLLECTION"}:
            return profile
        return "PRODUCTION"

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
        signal_history_ready = True
        candle_source: dict[str, Any] = {
            "symbol": symbol,
            "source": "UNKNOWN",
            "broker_source": "UNKNOWN",
            "account_login": "",
            "server": "",
            "account_type": "",
            "signal_history_ready": False,
            "history_required_candles": self.history_required_candles,
            "cache_source": "MT5_BACKFILL",
            "timeframes": {},
        }
        for timeframe in self.timeframes:
            history = self.backfill_service.fetch_history(symbol, timeframe, count=self.history_preload_candles)
            candles = history.get("candles", [])
            loaded_count = int(history.get("returned_count") or len(candles))
            timeframe_ready = str(history.get("status") or "").upper() == "OK" and loaded_count >= self.history_required_candles
            signal_history_ready = signal_history_ready and timeframe_ready
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
                "requested_count": history.get("requested_count", self.history_preload_candles),
                "returned_count": loaded_count,
                "last_candle_timestamp": candles[-1].get("time") if candles else None,
                "status": history.get("status"),
                "source": history.get("source", candle_source["source"]),
                "broker_source": history.get("broker_source", candle_source["broker_source"]),
                "requested_symbol": history.get("requested_symbol", symbol),
                "resolved_symbol": history.get("resolved_symbol", symbol),
                "mt5_last_error": history.get("mt5_last_error"),
                "process_id": history.get("process_id"),
                "connection_id": history.get("connection_id"),
                "cache_hit": history.get("cache_hit") is True,
                "cache_reason": history.get("cache_reason"),
                "history_ready": timeframe_ready,
            }
            if not timeframe_ready:
                blockers.append(f"{timeframe} history has insufficient real candles.")
        candle_source["signal_history_ready"] = signal_history_ready
        candle_source["signal_m15_count"] = int(candle_source["timeframes"].get("M15", {}).get("returned_count") or 0)
        candle_source["signal_h1_count"] = int(candle_source["timeframes"].get("H1", {}).get("returned_count") or 0)
        candle_source["signal_h4_count"] = int(candle_source["timeframes"].get("H4", {}).get("returned_count") or 0)
        return {"timeframes": timeframes, "validation": validation, "blockers": blockers, "candle_source": candle_source, "signal_history_ready": signal_history_ready}

    def _validator_diagnostics(
        self,
        symbol: str,
        feed: dict[str, Any],
        validation_status: str,
        rejection_reason: str,
        default_timeframe: str = "M15",
    ) -> dict[str, Any]:
        candle_source = feed.get("candle_source") if isinstance(feed, dict) else {}
        timeframe_reports = candle_source.get("timeframes", {}) if isinstance(candle_source, dict) else {}
        failed_timeframe = ""
        failed_report: dict[str, Any] | None = None
        for timeframe in self.timeframes:
            report = timeframe_reports.get(timeframe, {}) if isinstance(timeframe_reports, dict) else {}
            returned_count = int(report.get("returned_count") or 0)
            status = str(report.get("status") or "").upper()
            if status != "OK" or returned_count < self.history_required_candles:
                failed_timeframe = timeframe
                failed_report = report
                break
        timeframe = failed_timeframe or default_timeframe
        report = failed_report or (timeframe_reports.get(timeframe, {}) if isinstance(timeframe_reports, dict) else {})
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles_loaded": int(report.get("returned_count") or len(feed.get("timeframes", {}).get(timeframe, []))),
            "candles_required": self.history_required_candles,
            "data_source": str(report.get("source") or candle_source.get("source") or "REAL_SMC_MT5_MULTI_TIMEFRAME"),
            "validation_status": validation_status,
            "rejection_reason": rejection_reason,
        }

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
        status = str(tick.get("status") or "").upper()
        stale_age = self._number(tick.get("stale_age_seconds"))
        if stale_age is None:
            stale_age = 999999
        stale = status == "STALE_TICK" or bool(tick.get("stale"))
        acceptable = status in {"OK", "TICK_AVAILABLE_DIRECT"} and spread is not None and spread <= max_spread
        stale_within_grace = stale and spread is not None and spread <= max_spread and stale_age <= 10
        if acceptable and spread <= max_spread * 0.5:
            quality = 1.0
        elif acceptable or stale_within_grace:
            quality = 0.7
        else:
            quality = 0.0
        return {
            "spread": spread,
            "acceptable": acceptable,
            "stale_within_grace": stale_within_grace,
            "stale_age_seconds": stale_age,
            "status": status,
            "quality": quality,
            "max_spread": max_spread,
        }

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

    def _debug_confidence_components(
        self,
        score: dict[str, Any],
        smc: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
        volatility: dict[str, Any],
        trade_plan: dict[str, Any],
    ) -> dict[str, Any]:
        factors = score.get("factors", {})
        rr = self._number(trade_plan.get("risk_reward"))
        rr_pass = rr is not None and rr >= self.min_rr
        return {
            "trend_alignment_score": {"score": factors.get("trend_alignment", 0), "max_score": 20, "included_in_confidence": True},
            "bos_score": {"score": factors.get("bos_strength", 0), "max_score": 15, "included_in_confidence": True, "detected": bool(smc["bos"])},
            "choch_score": {
                "score": 0,
                "max_score": 0,
                "included_in_confidence": False,
                "detected": bool(smc["choch"]),
                "note": "CHOCH is audited but is not part of the current confidence sum.",
            },
            "liquidity_sweep_score": {"score": factors.get("liquidity_sweep_quality", 0), "max_score": 15, "included_in_confidence": True, "detected": bool(smc["liquidity_sweep"])},
            "fvg_score": {"score": factors.get("fvg_quality", 0), "max_score": 10, "included_in_confidence": True, "detected": bool(smc["fvg"])},
            "order_block_score": {"score": factors.get("order_block_quality", 0), "max_score": 10, "included_in_confidence": True, "detected": bool(smc["order_block"])},
            "session_score": {"score": factors.get("session_quality", 0), "max_score": 10, "included_in_confidence": True, "valid": bool(session["valid"]), "session": session["name"]},
            "spread_score": {"score": factors.get("spread_quality", 0), "max_score": 10, "included_in_confidence": True, "acceptable": bool(spread["acceptable"]), "spread": spread.get("spread"), "max_spread": spread.get("max_spread")},
            "volatility_score": {"score": factors.get("volatility_quality", 0), "max_score": 10, "included_in_confidence": True, "acceptable": bool(volatility["acceptable"]), "ratio": volatility.get("ratio")},
            "rr_score": {
                "score": 10 if rr_pass else 0,
                "max_score": 10,
                "included_in_confidence": False,
                "risk_reward": rr,
                "minimum_risk_reward": self.min_rr,
                "passed": rr_pass,
                "note": "RR is a final readiness gate but is not part of the current confidence sum.",
            },
        }

    def _debug_confidence_calculation(self, confidence_components: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
        included = {key: value for key, value in confidence_components.items() if value.get("included_in_confidence") is True}
        subtotal = round(sum(float(item.get("score", 0)) for item in included.values()), 2)
        return {
            "included_components": included,
            "excluded_diagnostics": {key: value for key, value in confidence_components.items() if value.get("included_in_confidence") is False},
            "formula": "trend_alignment + BOS + liquidity_sweep + FVG + order_block + session + spread + volatility",
            "subtotal_before_cap": subtotal,
            "cap": 100,
            "final_confidence": score["confidence"],
            "rating": score["rating"],
            "tradeable_threshold": self.tradeable_confidence,
            "confidence_gap_to_tradeable": max(0, self.tradeable_confidence - int(score["confidence"])),
        }

    def _empty_debug_components(self) -> dict[str, Any]:
        names = [
            "trend_alignment_score",
            "bos_score",
            "choch_score",
            "liquidity_sweep_score",
            "fvg_score",
            "order_block_score",
            "session_score",
            "spread_score",
            "volatility_score",
            "rr_score",
        ]
        return {name: {"score": 0, "included_in_confidence": name not in {"choch_score", "rr_score"}} for name in names}

    def _candle_counts(self, counts: dict[str, int]) -> dict[str, int]:
        return {
            "total_m15_candles_analyzed": counts.get("M15", 0),
            "total_h1_candles_analyzed": counts.get("H1", 0),
            "total_h4_candles_analyzed": counts.get("H4", 0),
        }

    def _market_regime(self, contexts: dict[str, dict[str, Any]]) -> str:
        biases = [contexts[timeframe]["bias"] for timeframe in self.timeframes]
        if all(bias == "bullish" for bias in biases) or all(bias == "bearish" for bias in biases):
            return "trend"
        if biases.count("ranging") >= 2:
            return "range"
        return "chop"

    def _direction_rejection_reasons(
        self,
        direction: str,
        signal: dict[str, Any],
        reasons: list[str],
        missing_requirements: list[dict[str, Any]],
    ) -> dict[str, str]:
        base = self._reason_text(reasons)
        missing = ", ".join(str(item.get("code") or item.get("label")) for item in missing_requirements)
        suffix = f" Missing requirements: {missing}." if missing else ""
        if signal.get("signal") == "BUY":
            return {"BUY": "BUY generated.", "SELL": f"SELL not generated because aligned direction is BUY.{suffix}"}
        if signal.get("signal") == "SELL":
            return {"BUY": f"BUY not generated because aligned direction is SELL.{suffix}", "SELL": "SELL generated."}
        if direction == "BUY":
            return {"BUY": f"BUY candidate failed readiness. {base}{suffix}", "SELL": f"SELL not generated because aligned direction is BUY.{suffix}"}
        if direction == "SELL":
            return {"BUY": f"BUY not generated because aligned direction is SELL.{suffix}", "SELL": f"SELL candidate failed readiness. {base}{suffix}"}
        return {"BUY": f"BUY not generated because M15/H1/H4 trend alignment does not support BUY. {base}{suffix}", "SELL": f"SELL not generated because M15/H1/H4 trend alignment does not support SELL. {base}{suffix}"}

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
        missing_requirements: list[dict[str, Any]] | None = None,
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
            "confidence_gap_to_75": max(0, self.tradeable_confidence - int(score["confidence"])),
            "confidence_threshold": self.tradeable_confidence,
            "session_result": "PASS" if session["valid"] else "FAIL",
            "spread_result": "PASS" if spread["acceptable"] else "FAIL",
            "missing_requirements": missing_requirements or [],
            "approval_model": "weighted_smc_score",
            "approval_note": "CHOCH and liquidity sweep add confidence but are not mandatory when weighted trend, BOS, FVG, order block, session, spread, volatility, and RR satisfy the approval threshold.",
        }

    def _profile_approval_audit(
        self,
        profile: str,
        signal_action: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
        reasons: list[str],
        missing_requirements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        audit = self._approval_audit(signal_action, score, smc, trade_plan, session, spread, reasons, missing_requirements)
        if profile == "DEMO_COLLECTION":
            threshold = self.demo_collection_confidence
            advisory = self._demo_collection_advisory_requirements(smc, session)
            audit.update(
                {
                    "strategy_profile": "DEMO_COLLECTION",
                    "status": "APPROVED" if signal_action in {"BUY", "SELL"} else ("REJECTED" if score["confidence"] >= threshold else "WAIT"),
                    "confirmation_score_required": 2,
                    "rr_result": "PASS" if self._number(trade_plan.get("risk_reward")) is not None and self._number(trade_plan.get("risk_reward")) >= self.demo_collection_min_rr else "FAIL",
                    "min_rr": self.demo_collection_min_rr,
                    "sl_tp_source": trade_plan.get("sl_tp_source") or "UNAVAILABLE",
                    "demo_risk_model": trade_plan.get("demo_risk_model"),
                    "advisory_requirements": advisory,
                    "relaxed_blockers": advisory,
                    "demo_collection_rules": {
                        "min_confidence": None,
                        "confirmation_score_required": 2,
                        "confirmation_pool": ["BOS", "FVG", "LIQUIDITY_SWEEP", "TREND_ALIGNMENT"],
                        "bos_mandatory": False,
                        "liquidity_sweep_mandatory": False,
                        "fvg_mandatory": False,
                        "order_block_mandatory": False,
                        "session_filter": "ADVISORY_BONUS_ONLY",
                        "requires_directional_bias": True,
                        "requires_h4_history": True,
                        "requires_m15_history": True,
                        "requires_valid_tick_spread": True,
                        "requires_sl_tp_valid_or_demo_risk_fallback": True,
                        "min_rr": self.demo_collection_min_rr,
                    },
                    "approval_note": "Round 3 DEMO_COLLECTION requires valid history, RR >= 2.0, acceptable spread, risk approval, higher-timeframe direction bias, and enough score from SMC edge confirmations. London/NY session is advisory bonus only.",
                }
            )
            return audit
        if profile != "AUTO_VALIDATION":
            audit["strategy_profile"] = "PRODUCTION"
            audit["production_rules_unchanged"] = True
            return audit

        threshold = self.auto_validation_confidence
        audit.update(
            {
                "strategy_profile": "AUTO_VALIDATION",
                "status": "APPROVED" if signal_action in {"BUY", "SELL"} else ("REJECTED" if score["confidence"] >= threshold else "WAIT"),
                "confidence_result": "PASS" if score["confidence"] >= threshold else "FAIL",
                "confidence_threshold": threshold,
                "confidence_gap_to_65": max(0, threshold - int(score["confidence"])),
                "bos_mandatory": False,
                "liquidity_sweep_mandatory": False,
                "spread_result": "PASS" if spread["acceptable"] or spread.get("stale_within_grace") else "FAIL",
                "spread_stale_within_grace": bool(spread.get("stale_within_grace")),
                "auto_validation_rules": {
                    "min_confidence": threshold,
                    "bos_mandatory": False,
                    "liquidity_sweep_mandatory": False,
                    "requires_buy_or_sell": True,
                    "requires_fvg": True,
                    "requires_order_block": True,
                    "requires_session_valid": True,
                    "requires_sl_tp_valid": True,
                    "min_rr": self.min_rr,
                    "requires_spread_acceptable_or_stale_within_grace": True,
                },
                "approval_note": "AUTO_VALIDATION is demo-only: BOS and liquidity sweep are confidence contributors, not hard gates. Production approval remains unchanged.",
            }
        )
        return audit

    def _missing_requirements(
        self,
        direction: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
    ) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        confidence_gap = max(0, self.tradeable_confidence - int(score["confidence"]))
        if confidence_gap > 0:
            missing.append({"code": "CONFIDENCE_GAP", "label": "Round 3 uses Score instead of the legacy confidence threshold.", "gap": confidence_gap})
        if direction not in {"BUY", "SELL"}:
            missing.append({"code": "TREND_ALIGNMENT_MISSING", "label": "M15/H1/H4 trend alignment is missing."})
        if not smc["bos"]:
            missing.append({"code": "BOS_MISSING", "label": "BOS confirmation is missing."})
        if not smc["liquidity_sweep"]:
            missing.append({"code": "LIQUIDITY_SWEEP_MISSING", "label": "Liquidity sweep is missing."})
        rr = self._number(trade_plan.get("risk_reward"))
        if rr is None:
            missing.append({"code": "RR_MISSING", "label": "Risk/reward is missing because the trade plan is incomplete."})
        elif rr < self.min_rr:
            missing.append({"code": "RR_LOW", "label": f"Risk/reward {rr:.2f}:1 is below {self.min_rr:.2f}:1.", "rr": rr})
        if not spread["acceptable"]:
            missing.append({"code": "SPREAD_TOO_HIGH", "label": "Spread is too high or unavailable.", "spread": spread.get("spread"), "max_spread": spread.get("max_spread")})
        if not session["valid"]:
            missing.append({"code": "SESSION_INVALID", "label": "Current time is outside the valid London/New York session."})
        entry = self._number(trade_plan.get("entry"))
        stop_loss = self._number(trade_plan.get("stop_loss"))
        take_profit = self._number(trade_plan.get("take_profit"))
        if direction == "BUY" and not (entry and stop_loss and take_profit and stop_loss < entry < take_profit):
            missing.append({"code": "SL_TP_INVALID", "label": "BUY SL/TP placement is invalid or incomplete."})
        if direction == "SELL" and not (entry and stop_loss and take_profit and take_profit < entry < stop_loss):
            missing.append({"code": "SL_TP_INVALID", "label": "SELL SL/TP placement is invalid or incomplete."})
        return missing

    def _auto_validation_tradeable(
        self,
        direction: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
    ) -> bool:
        rr = self._number(trade_plan.get("risk_reward"))
        return (
            direction in {"BUY", "SELL"}
            and int(score.get("confidence", 0)) >= self.auto_validation_confidence
            and bool(smc.get("fvg"))
            and bool(smc.get("order_block"))
            and bool(session.get("valid"))
            and self._sl_tp_valid(direction, trade_plan)
            and rr is not None
            and rr >= self.min_rr
            and (bool(spread.get("acceptable")) or bool(spread.get("stale_within_grace")))
        )

    def _auto_validation_missing_requirements(
        self,
        direction: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
    ) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        confidence_gap = max(0, self.auto_validation_confidence - int(score["confidence"]))
        if confidence_gap > 0:
            missing.append({"code": "CONFIDENCE_GAP", "label": f"Confidence needs +{confidence_gap} to reach 65.", "gap": confidence_gap})
        if direction not in {"BUY", "SELL"}:
            missing.append({"code": "TREND_ALIGNMENT_MISSING", "label": "AUTO validation requires a BUY or SELL direction."})
        if not smc.get("fvg"):
            missing.append({"code": "FVG_MISSING", "label": "AUTO validation requires FVG confirmation."})
        if not smc.get("order_block"):
            missing.append({"code": "ORDER_BLOCK_MISSING", "label": "AUTO validation requires order block confirmation."})
        rr = self._number(trade_plan.get("risk_reward"))
        if rr is None:
            missing.append({"code": "RR_MISSING", "label": "AUTO validation requires a complete trade plan with RR."})
        elif rr < self.min_rr:
            missing.append({"code": "RR_LOW", "label": f"Risk/reward {rr:.2f}:1 is below {self.min_rr:.2f}:1.", "rr": rr})
        if not (spread.get("acceptable") or spread.get("stale_within_grace")):
            missing.append(
                {
                    "code": "SPREAD_TOO_HIGH",
                    "label": "AUTO validation requires spread acceptable or stale within grace.",
                    "spread": spread.get("spread"),
                    "max_spread": spread.get("max_spread"),
                    "stale_within_grace": spread.get("stale_within_grace"),
                }
            )
        if not session.get("valid"):
            missing.append({"code": "SESSION_INVALID", "label": "AUTO validation requires a valid London/New York session."})
        if not self._sl_tp_valid(direction, trade_plan):
            missing.append({"code": "SL_TP_INVALID", "label": "AUTO validation requires valid SL/TP placement."})
        return missing

    def _demo_collection_direction(self, h4: dict[str, Any], h1: dict[str, Any], m15: dict[str, Any]) -> str:
        biases = [h4.get("bias"), h1.get("bias"), m15.get("bias")]
        bullish = biases.count("bullish")
        bearish = biases.count("bearish")
        if bullish > bearish and bullish > 0:
            return "BUY"
        if bearish > bullish and bearish > 0:
            return "SELL"
        return "WAIT"

    def _demo_collection_trade_plan(
        self,
        symbol: str,
        direction: str,
        tick: dict[str, Any],
        candles: list[dict[str, Any]],
        trade_plan: dict[str, Any],
    ) -> dict[str, Any]:
        if direction not in {"BUY", "SELL"}:
            return trade_plan
        rr = self._number(trade_plan.get("risk_reward"))
        if self._sl_tp_valid(direction, trade_plan) and rr is not None and rr >= self.demo_collection_min_rr:
            return {**trade_plan, "sl_tp_source": trade_plan.get("sl_tp_source") or "STRATEGY", "demo_risk_model": None}
        entry_key = "ask" if direction == "BUY" else "bid"
        entry = self._number(tick.get(entry_key))
        if entry is None or entry <= 0:
            return trade_plan
        atr = self._atr(candles[-20:]) if candles else 0
        fallback_risk = max(atr * 0.8, entry * (0.001 if symbol == "XAUUSD" else 0.0008))
        if fallback_risk <= 0:
            return trade_plan
        digits = 2 if symbol == "XAUUSD" else 5
        if direction == "BUY":
            stop_loss = entry - fallback_risk
            take_profit = entry + fallback_risk * self.demo_collection_min_rr
        else:
            stop_loss = entry + fallback_risk
            take_profit = entry - fallback_risk * self.demo_collection_min_rr
        risk = abs(entry - stop_loss)
        rr_value = abs(take_profit - entry) / risk if risk > 0 else 0
        return {
            "entry": round(entry, digits),
            "stop_loss": round(stop_loss, digits),
            "take_profit": round(take_profit, digits),
            "risk_reward": round(rr_value, 2),
            "sl_tp_source": "DEMO_RISK_FALLBACK",
            "demo_risk_model": {
                "model": "ATR_OR_FIXED_RISK",
                "atr": round(atr, digits),
                "risk_distance": round(fallback_risk, digits),
                "min_rr": self.demo_collection_min_rr,
            },
        }

    def _round3_history_audit(self, symbol: str, feed: dict[str, Any]) -> dict[str, Any]:
        candle_source = feed.get("candle_source") if isinstance(feed, dict) else {}
        reports = candle_source.get("timeframes", {}) if isinstance(candle_source, dict) else {}

        def history_passed(timeframe: str) -> bool:
            report = reports.get(timeframe, {}) if isinstance(reports, dict) else {}
            returned = int(report.get("returned_count") or len(feed.get("timeframes", {}).get(timeframe, [])))
            return str(report.get("status") or "").upper() == "OK" and returned >= self.history_required_candles

        passed_rules: list[str] = []
        failed_rules: list[str] = []
        h4_ok = history_passed("H4")
        m15_ok = history_passed("M15")
        (passed_rules if h4_ok else failed_rules).append("H4_HISTORY_AVAILABLE" if h4_ok else "H4_HISTORY_INSUFFICIENT")
        (passed_rules if m15_ok else failed_rules).append("M15_HISTORY_AVAILABLE" if m15_ok else "M15_HISTORY_INSUFFICIENT")
        reason = self._round3_reason(symbol, "REJECTED", failed_rules, None)
        return {
            "rule_name": "ROUND_3_STRICT_ENTRY_FILTERS",
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "advisory_warnings": [],
            "session": "UNAVAILABLE",
            "RR": None,
            "risk_reward": None,
            "required_rr": self.demo_collection_min_rr,
            "warmup_history_ready": bool(candle_source.get("signal_history_ready")),
            "signal_history_ready": bool(candle_source.get("signal_history_ready")),
            "warmup_h4_count": int(candle_source.get("signal_h4_count") or 0),
            "signal_h4_count": int(candle_source.get("signal_h4_count") or 0),
            "signal_m15_count": int(candle_source.get("signal_m15_count") or 0),
            "signal_h1_count": int(candle_source.get("signal_h1_count") or 0),
            "cache_source": candle_source.get("cache_source") or "MT5_BACKFILL",
            "signal_source": "REAL_SMC_MT5_MULTI_TIMEFRAME",
            "bos_status": "UNAVAILABLE",
            "fvg_status": "UNAVAILABLE",
            "h4_history_status": "AVAILABLE" if h4_ok else "INSUFFICIENT",
            "m15_history_status": "AVAILABLE" if m15_ok else "INSUFFICIENT",
            "final_decision": "REJECTED",
            "final_decision_reason": reason,
            "rejection_reason": reason,
        }

    def _round3_rule_audit(
        self,
        symbol: str,
        feed: dict[str, Any],
        direction: str,
        smc: dict[str, Any],
        session: dict[str, Any],
        trade_plan: dict[str, Any],
        score: dict[str, Any],
        spread: dict[str, Any],
    ) -> dict[str, Any]:
        history = self._round3_history_audit(symbol, feed)
        passed_rules = [rule for rule in history["passed_rules"]]
        failed_rules = [rule for rule in history["failed_rules"]]
        rr = self._number(trade_plan.get("risk_reward"))
        confirmations = self._round3_confirmation_summary(direction, smc, score)
        checks = [
            ("RR_2_0_OR_HIGHER", "RR_BELOW_2_0", rr is not None and rr >= self.demo_collection_min_rr),
            ("SPREAD_ACCEPTABLE", "SPREAD_TOO_HIGH", bool(spread.get("acceptable"))),
            ("RISK_APPROVED", "RISK_REJECTED", direction in {"BUY", "SELL"} and self._sl_tp_valid(direction, trade_plan)),
            ("DIRECTION_MATCHES_HIGHER_TIMEFRAME_BIAS", "DIRECTION_BIAS_MISMATCH", confirmations["direction_valid"]),
            ("STRONG_CONFIRMATIONS_2_PLUS", "STRONG_CONFIRMATIONS_BELOW_2", confirmations["strong_count"] >= 2),
            ("ROUND_3_SCORE_THRESHOLD", "ROUND_3_SCORE_BELOW_THRESHOLD", confirmations["score"] >= confirmations["required_score"]),
        ]
        for passed_code, failed_code, passed in checks:
            (passed_rules if passed else failed_rules).append(passed_code if passed else failed_code)
        advisory_warnings: list[str] = []
        advisory_warnings.extend(f"{code}_MISSING" for code in confirmations["missing_codes"])
        decision = "ACCEPTED" if not failed_rules else "REJECTED"
        reason = self._round3_reason(symbol, decision, failed_rules, rr, confirmations, session)
        return {
            "rule_name": "ROUND_3_EDGE_SCORE_FILTERS",
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "advisory_warnings": advisory_warnings,
            "session": session.get("name") or "UNAVAILABLE",
            "RR": rr,
            "risk_reward": rr,
            "required_rr": self.demo_collection_min_rr,
            "warmup_history_ready": bool(history.get("signal_history_ready")),
            "signal_history_ready": bool(history.get("signal_history_ready")),
            "warmup_h4_count": int(history.get("signal_h4_count") or 0),
            "signal_h4_count": int(history.get("signal_h4_count") or 0),
            "signal_m15_count": int(history.get("signal_m15_count") or 0),
            "signal_h1_count": int(history.get("signal_h1_count") or 0),
            "cache_source": feed.get("candle_source", {}).get("cache_source") if isinstance(feed.get("candle_source"), dict) else "MT5_BACKFILL",
            "signal_source": "REAL_SMC_MT5_MULTI_TIMEFRAME",
            "confirmation_score": confirmations["score"],
            "confirmation_required": confirmations["required_score"],
            "confirmation_total": confirmations["total"],
            "strong_confirmation_count": confirmations["strong_count"],
            "strong_confirmation_required": 2,
            "confirmation_passed": confirmations["passed_labels"],
            "confirmation_missing": confirmations["missing_labels"],
            "advisory_session_bonus": bool(session.get("valid")),
            "confirmation_states": confirmations["states"],
            "bos_status": "PRESENT" if smc.get("bos") else "MISSING",
            "fvg_status": "PRESENT" if smc.get("fvg") else "MISSING",
            "liquidity_sweep_status": "PRESENT" if smc.get("liquidity_sweep") else "MISSING",
            "trend_alignment_status": "ALIGNED" if confirmations["states"].get("TREND_ALIGNMENT") else "NOT_ALIGNED",
            "direction_bias_status": "MATCHED" if confirmations["direction_valid"] else "MISMATCHED",
            "h4_history_status": history["h4_history_status"],
            "m15_history_status": history["m15_history_status"],
            "final_decision": decision,
            "final_decision_reason": reason,
            "rejection_reason": "" if decision == "ACCEPTED" else reason,
        }

    def _round3_confirmation_summary(self, direction: str, smc: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
        trend_aligned = direction in {"BUY", "SELL"} and int(score.get("factors", {}).get("trend_alignment", 0)) > 0
        factors = score.get("factors", {}) if isinstance(score.get("factors"), dict) else {}
        fvg = bool(smc.get("fvg") or smc.get("imbalance") or smc.get("imbalance_zone"))
        pullback = bool(smc.get("pullback") or smc.get("retest") or smc.get("entry_zone_valid") or smc.get("near_fvg") or factors.get("entry_zone"))
        momentum = bool(smc.get("momentum") or smc.get("displacement") or smc.get("displacement_candle") or int(factors.get("displacement", 0)) > 0)
        atr_ok = bool(smc.get("atr_valid") or smc.get("atr_tradeable") or smc.get("volatility_tradeable") or int(factors.get("volatility", 0)) > 0)
        spread_clean = int(factors.get("spread", 0)) > 0 or bool(smc.get("spread_clean"))
        rr_ok = int(factors.get("rr", 0)) > 0 or bool(smc.get("rr_2_0"))
        session_bonus = int(factors.get("session", 0)) > 0 or bool(smc.get("session_valid"))
        states = {
            "TREND_ALIGNMENT": trend_aligned,
            "LIQUIDITY_SWEEP": bool(smc.get("liquidity_sweep")),
            "BOS": bool(smc.get("bos") or smc.get("structure_confirmation")),
            "FVG_IMBALANCE": fvg,
            "PULLBACK_RETEST": pullback,
            "MOMENTUM_DISPLACEMENT": momentum,
            "ATR_VOLATILITY": atr_ok,
            "SPREAD_CLEAN": spread_clean,
            "RR_2_0": rr_ok,
            "SESSION_LONDON_NY_BONUS": session_bonus,
        }
        labels = {
            "TREND_ALIGNMENT": "H4/H1 trend alignment",
            "LIQUIDITY_SWEEP": "liquidity sweep",
            "BOS": "BOS",
            "FVG_IMBALANCE": "FVG/imbalance",
            "PULLBACK_RETEST": "pullback/retest",
            "MOMENTUM_DISPLACEMENT": "momentum/displacement",
            "ATR_VOLATILITY": "ATR volatility",
            "SPREAD_CLEAN": "clean spread",
            "RR_2_0": "RR >= 2.0",
            "SESSION_LONDON_NY_BONUS": "London/NY session",
        }
        strong_codes = {"TREND_ALIGNMENT", "LIQUIDITY_SWEEP", "BOS", "FVG_IMBALANCE", "PULLBACK_RETEST", "MOMENTUM_DISPLACEMENT"}
        passed_codes = [code for code, passed in states.items() if passed]
        missing_codes = [code for code, passed in states.items() if not passed]
        return {
            "score": len(passed_codes),
            "required_score": 5,
            "total": len(states),
            "strong_count": len([code for code in passed_codes if code in strong_codes]),
            "direction_valid": direction in {"BUY", "SELL"} and trend_aligned,
            "direction": direction,
            "trend_bias": direction if trend_aligned else "UNCLEAR",
            "states": states,
            "passed_codes": passed_codes,
            "missing_codes": missing_codes,
            "passed_labels": [labels[code] for code in passed_codes],
            "missing_labels": [labels[code] for code in missing_codes],
        }

    def _join_labels(self, labels: list[str]) -> str:
        if not labels:
            return ""
        if len(labels) == 1:
            return labels[0]
        if len(labels) == 2:
            return f"{labels[0]} and {labels[1]}"
        return f"{', '.join(labels[:-1])}, and {labels[-1]}"

    def _round3_reason(self, symbol: str, decision: str, failed_rules: list[str], rr: float | None, confirmations: dict[str, Any] | None = None, session: dict[str, Any] | None = None) -> str:
        confirmations = confirmations or {"score": 0, "required_score": 5, "strong_count": 0, "passed_labels": [], "missing_labels": ["BOS", "FVG/imbalance", "liquidity sweep", "trend alignment"]}
        first_failure = failed_rules[0] if failed_rules else ""
        if decision == "ACCEPTED":
            rr_text = f"{rr:.1f}" if rr is not None else "2.0"
            passed = self._join_labels(list(confirmations.get("passed_labels") or [])) or "score"
            return f"Accepted: Round 3 score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)} with {passed}. Direction {confirmations.get('direction')}. Trend {confirmations.get('trend_bias')}. RR {rr_text}. Risk approved."
        if first_failure == "H4_HISTORY_INSUFFICIENT":
            return f"{symbol} rejected because H4 history was insufficient."
        if first_failure == "M15_HISTORY_INSUFFICIENT":
            return f"{symbol} rejected because M15 history was insufficient."
        if first_failure == "RR_BELOW_2_0":
            rr_text = f"{rr:.1f}" if rr is not None else "missing"
            return f"Rejected: RR {rr_text} below required 2.0."
        if first_failure == "SPREAD_TOO_HIGH":
            return "Rejected: spread too high."
        if first_failure == "RISK_REJECTED":
            return "Rejected: risk validation failed."
        if first_failure == "DIRECTION_BIAS_MISMATCH":
            return f"Rejected: direction {confirmations.get('direction') or 'unclear'} does not match higher-timeframe bias."
        if first_failure == "STRONG_CONFIRMATIONS_BELOW_2":
            missing = self._join_labels(list(confirmations.get("missing_labels") or []))
            return f"Waiting: strong confirmations {int(confirmations.get('strong_count') or 0)}/2. Missing {missing}." if missing else f"Waiting: strong confirmations {int(confirmations.get('strong_count') or 0)}/2."
        if first_failure == "ROUND_3_SCORE_BELOW_THRESHOLD":
            missing = self._join_labels(list(confirmations.get("missing_labels") or []))
            return f"Waiting: Score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)}. Missing {missing}." if missing else f"Waiting: Score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)}."
        return f"Waiting: Score {int(confirmations.get('score') or 0)}/{int(confirmations.get('required_score') or 5)}."

    def _demo_collection_tradeable(
        self,
        direction: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
        round3_audit: dict[str, Any],
    ) -> bool:
        rr = self._number(trade_plan.get("risk_reward"))
        confirmations = self._round3_confirmation_summary(direction, smc, score)
        return (
            direction in {"BUY", "SELL"}
            and not round3_audit.get("failed_rules")
            and self._sl_tp_valid(direction, trade_plan)
            and rr is not None
            and rr >= self.demo_collection_min_rr
            and bool(spread.get("acceptable"))
            and confirmations["strong_count"] >= 2
            and confirmations["score"] >= confirmations["required_score"]
            and confirmations["direction_valid"]
        )

    def _demo_collection_missing_requirements(
        self,
        direction: str,
        score: dict[str, Any],
        smc: dict[str, Any],
        trade_plan: dict[str, Any],
        session: dict[str, Any],
        spread: dict[str, Any],
    ) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        if direction not in {"BUY", "SELL"}:
            missing.append({"code": "DIRECTIONAL_BIAS_MISSING", "label": "DEMO_COLLECTION requires a BUY or SELL directional bias."})
        confirmations = self._round3_confirmation_summary(direction, smc, score)
        if confirmations["strong_count"] < 2:
            missing.append({
                "code": "CONFIRMATION_SCORE_LOW",
                "label": f"Round 3 needs at least 2 strong confirmations; current strong count is {confirmations['strong_count']}/2.",
                "confirmation_score": confirmations["score"],
                "confirmation_required": confirmations["required_score"],
                "strong_confirmation_count": confirmations["strong_count"],
                "missing": confirmations["missing_labels"],
            })
        elif confirmations["score"] < confirmations["required_score"]:
            missing.append({
                "code": "CONFIRMATION_SCORE_LOW",
                "label": f"Round 3 needs Score {confirmations['required_score']}/{confirmations['total']}; current Score is {confirmations['score']}/{confirmations['total']}.",
                "confirmation_score": confirmations["score"],
                "confirmation_required": confirmations["required_score"],
                "missing": confirmations["missing_labels"],
            })
        if not confirmations["direction_valid"]:
            missing.append({"code": "DIRECTION_BIAS_MISMATCH", "label": "Trade direction must match higher-timeframe bias."})
        rr = self._number(trade_plan.get("risk_reward"))
        if rr is None:
            missing.append({"code": "RR_MISSING", "label": "DEMO_COLLECTION requires RR from strategy plan or fallback demo risk model."})
        elif rr < self.demo_collection_min_rr:
            missing.append({"code": "RR_LOW", "label": f"Risk/reward {rr:.2f}:1 is below {self.demo_collection_min_rr:.2f}:1.", "rr": rr})
        if not spread.get("acceptable"):
            missing.append({"code": "SPREAD_TOO_HIGH", "label": "DEMO_COLLECTION requires a live acceptable tick/spread.", "spread": spread.get("spread"), "max_spread": spread.get("max_spread")})
        if not self._sl_tp_valid(direction, trade_plan):
            missing.append({"code": "SL_TP_INVALID", "label": "DEMO_COLLECTION requires valid SL/TP placement from strategy or fallback demo risk model."})
        for advisory in self._demo_collection_advisory_requirements(smc, session):
            missing.append({**advisory, "advisory": True})
        return missing

    def _demo_collection_advisory_requirements(self, smc: dict[str, Any], session: dict[str, Any]) -> list[dict[str, Any]]:
        advisory: list[dict[str, Any]] = []
        if not smc.get("liquidity_sweep"):
            advisory.append({"code": "LIQUIDITY_SWEEP_MISSING", "label": "Liquidity sweep missing; advisory confidence only."})
        if not smc.get("order_block"):
            advisory.append({"code": "ORDER_BLOCK_MISSING", "label": "Order block missing; advisory confidence only."})
        return advisory

    def _profile_confidence(self, profile: str) -> int:
        if profile == "DEMO_COLLECTION":
            return self.demo_collection_confidence
        if profile == "AUTO_VALIDATION":
            return self.auto_validation_confidence
        return self.watchlist_confidence

    def _sl_tp_valid(self, direction: str, trade_plan: dict[str, Any]) -> bool:
        entry = self._number(trade_plan.get("entry"))
        stop_loss = self._number(trade_plan.get("stop_loss"))
        take_profit = self._number(trade_plan.get("take_profit"))
        if direction == "BUY":
            return bool(entry and stop_loss and take_profit and stop_loss < entry < take_profit)
        if direction == "SELL":
            return bool(entry and stop_loss and take_profit and take_profit < entry < stop_loss)
        return False

    def _status_level(self, signal_action: str, score: dict[str, Any], missing_requirements: list[dict[str, Any]]) -> str:
        if signal_action in {"BUY", "SELL"}:
            return "READY_FOR_PREVIEW"
        confidence = int(score.get("confidence", 0))
        if self.watchlist_confidence <= confidence < self.tradeable_confidence:
            return "WATCHLIST"
        if any(item.get("code") in {"SPREAD_TOO_HIGH", "SL_TP_INVALID"} for item in missing_requirements):
            return "REJECTED"
        return "WAIT"

    def _profile_status_level(self, signal_action: str, score: dict[str, Any], missing_requirements: list[dict[str, Any]], threshold: int) -> str:
        if signal_action in {"BUY", "SELL"}:
            return "READY_FOR_PREVIEW"
        confidence = int(score.get("confidence", 0))
        if any(item.get("code") in {"SPREAD_TOO_HIGH", "SL_TP_INVALID", "RR_MISSING", "RR_LOW", "DIRECTION_BIAS_MISMATCH"} for item in missing_requirements):
            return "REJECTED"
        if any(item.get("code") == "CONFIRMATION_SCORE_LOW" for item in missing_requirements):
            return "WAIT"
        if confidence >= threshold:
            return "WATCHLIST"
        return "WAIT"

    def _profile_reasons(self, profile: str, reasons: list[str], missing_requirements: list[dict[str, Any]]) -> list[str]:
        if profile == "DEMO_COLLECTION":
            hard_missing = [item for item in missing_requirements if not item.get("advisory")]
            if not hard_missing:
                return ["Round 3 approved: valid history, RR >= 2.0, spread, risk, direction bias, and edge score passed."]
            return ["Round 3 active: require valid history, RR >= 2.0, spread, risk approval, direction bias, and enough edge score."]
        if profile != "AUTO_VALIDATION":
            return reasons
        if not missing_requirements:
            return ["AUTO_VALIDATION profile approved for demo validation: direction, FVG, order block, session, SL/TP, RR, and spread checks passed without requiring BOS or liquidity sweep."]
        filtered = [
            reason
            for reason in reasons
            if "Liquidity sweep" not in reason and "Break of structure" not in reason and "tradeable threshold is 75" not in reason
        ]
        filtered.insert(0, "AUTO_VALIDATION profile active: BOS and liquidity sweep are not hard gates for demo validation.")
        return filtered

    def _next_steps(self, missing_requirements: list[dict[str, Any]], score: dict[str, Any], confidence_threshold: int | None = None) -> str:
        threshold = confidence_threshold or self.tradeable_confidence
        if not missing_requirements:
            return "All preview requirements are currently satisfied."
        priority = [item["code"] for item in missing_requirements[:3]]
        names = {
            "CONFIDENCE_GAP": "Score to reach 2 confirmations",
            "BOS_MISSING": "BOS confirmation",
            "LIQUIDITY_SWEEP_MISSING": "liquidity sweep",
            "RR_MISSING": "valid RR",
            "RR_LOW": "higher RR",
            "SPREAD_TOO_HIGH": "spread to narrow",
            "SESSION_INVALID": "London/New York session bonus",
            "SL_TP_INVALID": "valid SL/TP placement",
            "TREND_ALIGNMENT_MISSING": "M15/H1/H4 trend alignment",
            "DIRECTIONAL_BIAS_MISSING": "directional bias",
            "FVG_MISSING": "FVG confirmation",
            "ORDER_BLOCK_MISSING": "order block confirmation",
        }
        readable = [names.get(code, code.replace("_", " ").lower()) for code in priority]
        if len(readable) == 1:
            needed = readable[0]
        else:
            needed = ", ".join(readable[:-1]) + f" and {readable[-1]}"
        return f"Need {needed}. Current confidence {score['confidence']}/{threshold}."

    def _wait(self, symbol: str, reasons: list[str], risk_status: str = "NO_SIGNAL", feed: dict[str, Any] | None = None) -> dict[str, Any]:
        reason_text = self._reason_text(reasons)
        validation_status = "BLOCKED" if risk_status == "INSUFFICIENT_DATA" else "WAITING"
        validator_diagnostics = self._validator_diagnostics(symbol, feed or {}, validation_status, reason_text)
        return {
            "symbol": symbol,
            "signal": "WAIT",
            "status_level": "REJECTED" if risk_status in {"INSUFFICIENT_DATA", "REJECTED"} else "WAIT",
            "confidence": None,
            "reason": reason_text,
            "what_needs_to_happen_next": reason_text,
            "missing_requirements": [{"code": "INSUFFICIENT_DATA", "label": reason_text}],
            "setup_reason": reason_text,
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
                "final_approval_reason": reason_text,
                "confidence_result": "INSUFFICIENT_DATA",
                "missing_requirements": [{"code": "INSUFFICIENT_DATA", "label": reason_text}],
            },
            "candle_source": (feed or {}).get("candle_source", {"symbol": symbol, "timeframes": {}}),
            "data_source": "REAL_SMC_MT5_MULTI_TIMEFRAME",
            **validator_diagnostics,
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
