from typing import Any

from backend.strategy_engine.strategy_models import ConfluenceScoreBreakdown


class ConfluenceScoreEngine:
    """Combine XAUUSD strategy contexts into one confidence and trade-quality breakdown."""

    MAX_RAW_SCORE = 190.0

    def score(
        self,
        session_context: Any,
        indicator_context: Any,
        liquidity_context: Any,
        smc_context: Any,
        regime_context: Any,
        news_filter_decision: Any | None = None,
        macro_context: Any | None = None,
    ) -> ConfluenceScoreBreakdown:
        breakdown = ConfluenceScoreBreakdown()
        aligned: list[str] = []
        missing: list[str] = []
        warnings: list[str] = []

        breakdown.session_score = self._session_score(session_context, aligned, missing)
        breakdown.indicator_score = self._indicator_score(indicator_context, aligned, missing)
        breakdown.liquidity_score = self._liquidity_score(liquidity_context, aligned, missing)
        breakdown.structure_score = self._structure_score(smc_context, aligned, missing)
        breakdown.fvg_score = self._fvg_score(smc_context, aligned, missing)
        breakdown.order_block_score = self._order_block_score(smc_context, aligned, missing)
        breakdown.regime_score = self._regime_score(regime_context, aligned, missing, warnings)
        breakdown.total_score = round(
            breakdown.session_score
            + breakdown.indicator_score
            + breakdown.liquidity_score
            + breakdown.structure_score
            + breakdown.fvg_score
            + breakdown.order_block_score
            + breakdown.regime_score,
            2,
        )

        confidence = round(min((breakdown.total_score / self.MAX_RAW_SCORE) * 100, 100.0), 2)
        confidence = self._apply_caps(confidence, session_context, liquidity_context, smc_context, regime_context, warnings)
        breakdown.confidence = confidence
        breakdown.trade_quality = self._trade_quality(confidence)
        breakdown.risk_mode = self._risk_mode(breakdown.trade_quality, regime_context)
        if self._get(regime_context, "risk_mode", "NO_TRADE") == "NO_TRADE":
            breakdown.trade_quality = "NO_TRADE"
            breakdown.risk_mode = "NO_TRADE"
            breakdown.confidence = min(breakdown.confidence, 20.0)
            warnings.append("Market regime risk mode is NO_TRADE; confluence is hard-blocked.")
        self._apply_news_decision(breakdown, news_filter_decision, warnings)
        self._apply_macro_context(breakdown, macro_context, warnings)

        breakdown.aligned_confirmations = aligned
        breakdown.missing_confirmations = missing
        breakdown.warnings = warnings
        return breakdown

    def _apply_news_decision(
        self,
        breakdown: ConfluenceScoreBreakdown,
        news_filter_decision: Any | None,
        warnings: list[str],
    ) -> None:
        if news_filter_decision is None:
            return
        if self._get(news_filter_decision, "blocked", False):
            cap = self._get(news_filter_decision, "confidence_cap", 0.0)
            breakdown.confidence = min(breakdown.confidence, float(cap if cap is not None else 0.0))
            breakdown.trade_quality = "NO_TRADE"
            breakdown.risk_mode = "NO_TRADE"
            warnings.append(self._get(news_filter_decision, "technical_message", "News filter blocked confluence."))
            return
        penalty = float(self._get(news_filter_decision, "confidence_penalty", 0.0) or 0.0)
        if penalty > 0:
            breakdown.confidence = round(max(0.0, breakdown.confidence - penalty), 2)
            breakdown.trade_quality = self._trade_quality(breakdown.confidence)
            breakdown.risk_mode = "REDUCED_RISK"
            warnings.append(self._get(news_filter_decision, "technical_message", "News filter reduced confluence."))

    def _apply_macro_context(
        self,
        breakdown: ConfluenceScoreBreakdown,
        macro_context: Any | None,
        warnings: list[str],
    ) -> None:
        if macro_context is None:
            return
        adjustment = float(self._get(macro_context, "confidence_adjustment", 0.0) or 0.0)
        if adjustment and breakdown.risk_mode != "NO_TRADE":
            breakdown.confidence = round(max(0.0, min(100.0, breakdown.confidence + adjustment)), 2)
            breakdown.trade_quality = self._trade_quality(breakdown.confidence)
            warnings.append(self._get(macro_context, "reason", "Macro context adjusted confidence."))
        if self._get(macro_context, "macro_alignment", "UNKNOWN") == "CONFLICTING":
            breakdown.trade_quality = self._degrade_quality(breakdown.trade_quality)
            if breakdown.risk_mode != "NO_TRADE":
                breakdown.risk_mode = "REDUCED_RISK"
            warnings.append("Macro conflict degraded trade quality by one level.")

    def _degrade_quality(self, quality: str) -> str:
        order = ["A_PLUS", "A", "B", "C", "NO_TRADE"]
        if quality not in order:
            return "NO_TRADE"
        return order[min(order.index(quality) + 1, len(order) - 1)]

    def _session_score(self, session_context: Any, aligned: list[str], missing: list[str]) -> float:
        quality = self._get(session_context, "session_quality", "LOW")
        session = self._get(session_context, "current_session", "OFF_SESSION")
        if quality == "HIGH":
            aligned.append(f"High-quality {session} session")
            return 10.0
        if quality == "MEDIUM":
            aligned.append(f"Medium-quality {session} session")
            return 5.0
        missing.append("London/New York session timing")
        return 0.0

    def _indicator_score(self, indicator_context: Any, aligned: list[str], missing: list[str]) -> float:
        score = 0.0
        if self._get(indicator_context, "trend_bias", "NEUTRAL") != "NEUTRAL":
            score += 10.0
            aligned.append("Higher-timeframe trend bias")
        else:
            missing.append("Higher-timeframe trend bias")
        if self._get(indicator_context, "rsi", None) is not None:
            score += 5.0
            aligned.append("RSI filter available")
        else:
            missing.append("RSI filter")
        if self._get(indicator_context, "volatility_state", "NORMAL") == "NORMAL":
            score += 5.0
            aligned.append("Normal ATR volatility")
        else:
            missing.append("Normal ATR volatility")
        return score

    def _liquidity_score(self, liquidity_context: Any, aligned: list[str], missing: list[str]) -> float:
        score = 0.0
        if self._get(liquidity_context, "sweep_direction", "NONE") != "NONE":
            score += 20.0
            aligned.append("Liquidity sweep")
        else:
            missing.append("Liquidity sweep")
        if self._get(liquidity_context, "rejection_detected", False):
            score += 10.0
            aligned.append("Sweep rejection")
        else:
            missing.append("Sweep rejection")
        if self._get(liquidity_context, "sweep_quality", "NONE") == "HIGH":
            score += 10.0
            aligned.append("High-quality sweep")
        else:
            missing.append("High-quality sweep")
        return score

    def _structure_score(self, smc_context: Any, aligned: list[str], missing: list[str]) -> float:
        score = 0.0
        if self._has_structure_shift(smc_context):
            score += 20.0
            aligned.append("BOS/CHOCH structure shift")
        else:
            missing.append("BOS/CHOCH structure shift")
        if self._get(smc_context, "post_sweep_confirmation", False):
            score += 15.0
            aligned.append("Post-sweep structure confirmation")
        else:
            missing.append("Post-sweep structure confirmation")
        if self._get(smc_context, "structure_quality", "NONE") == "HIGH":
            score += 10.0
            aligned.append("High-quality structure")
        else:
            missing.append("High-quality structure")
        return score

    def _fvg_score(self, smc_context: Any, aligned: list[str], missing: list[str]) -> float:
        latest = self._get(smc_context, "latest_fvg", None)
        active_aligned = bool(self._get(smc_context, "active_fvg_detected", False)) and latest is not None and (
            self._get(latest, "aligned_with_structure", False) or self._get(latest, "aligned_with_liquidity", False)
        )
        score = 0.0
        if active_aligned:
            score += 15.0
            aligned.append("Active aligned FVG")
        else:
            missing.append("Active aligned FVG")
        if self._get(smc_context, "fvg_quality", "NONE") == "HIGH":
            score += 10.0
            aligned.append("High-quality FVG")
        else:
            missing.append("High-quality FVG")
        return score

    def _order_block_score(self, smc_context: Any, aligned: list[str], missing: list[str]) -> float:
        latest = self._get(smc_context, "latest_order_block", None)
        active_aligned = bool(self._get(smc_context, "active_order_block_detected", False)) and latest is not None and (
            self._get(latest, "aligned_with_structure", False)
            or self._get(latest, "aligned_with_liquidity", False)
            or self._get(latest, "aligned_with_fvg", False)
        )
        score = 0.0
        if active_aligned:
            score += 15.0
            aligned.append("Active aligned order block")
        else:
            missing.append("Active aligned order block")
        if latest is not None and (self._get(latest, "fresh", False) or self._get(latest, "quality", "NONE") == "HIGH"):
            score += 10.0
            aligned.append("Fresh or high-quality order block")
        else:
            missing.append("Fresh or high-quality order block")
        return score

    def _regime_score(self, regime_context: Any, aligned: list[str], missing: list[str], warnings: list[str]) -> float:
        score = 0.0
        regime = self._get(regime_context, "regime", "UNCLEAR")
        tradeability = self._get(regime_context, "tradeability", "AVOID")
        if regime == "TRENDING":
            score += 15.0
            aligned.append("Trending market regime")
        else:
            missing.append("Trending market regime")
        if tradeability == "HIGH":
            score += 10.0
            aligned.append("High regime tradeability")
        else:
            missing.append("High regime tradeability")
        if self._get(regime_context, "risk_mode", "NO_TRADE") == "NO_TRADE" or tradeability == "AVOID":
            warnings.append("Avoid/no-trade regime condition detected.")
        return score

    def _apply_caps(
        self,
        confidence: float,
        session_context: Any,
        liquidity_context: Any,
        smc_context: Any,
        regime_context: Any,
        warnings: list[str],
    ) -> float:
        capped = confidence
        if self._get(liquidity_context, "sweep_direction", "NONE") == "NONE":
            capped = min(capped, 40.0)
            warnings.append("Confidence capped at 40 because no liquidity sweep is present.")
        if not self._has_structure_shift(smc_context):
            capped = min(capped, 50.0)
            warnings.append("Confidence capped at 50 because no BOS/CHOCH is present.")
        if not self._get(smc_context, "active_fvg_detected", False) and not self._get(smc_context, "active_order_block_detected", False):
            capped = min(capped, 60.0)
            warnings.append("Confidence capped at 60 because no active FVG or order block is present.")
        if self._get(session_context, "session_quality", "LOW") == "LOW":
            capped = min(capped, 50.0)
            warnings.append("Confidence capped at 50 because session quality is LOW.")
        if self._get(regime_context, "risk_mode", "NO_TRADE") == "NO_TRADE":
            capped = min(capped, 20.0)
        return round(capped, 2)

    def _trade_quality(self, confidence: float) -> str:
        if confidence >= 85:
            return "A_PLUS"
        if confidence >= 75:
            return "A"
        if confidence >= 60:
            return "B"
        if confidence >= 45:
            return "C"
        return "NO_TRADE"

    def _risk_mode(self, trade_quality: str, regime_context: Any) -> str:
        regime_risk = self._get(regime_context, "risk_mode", "NO_TRADE")
        if regime_risk == "NO_TRADE" or trade_quality == "NO_TRADE":
            return "NO_TRADE"
        if regime_risk == "REDUCED_RISK" or trade_quality == "C":
            return "REDUCED_RISK"
        return "NORMAL"

    def _has_structure_shift(self, smc_context: Any) -> bool:
        return self._get(smc_context, "bos_direction", "NONE") != "NONE" or self._get(smc_context, "choch_direction", "NONE") != "NONE"

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
