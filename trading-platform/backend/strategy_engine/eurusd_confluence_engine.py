from typing import Any

from backend.strategy_engine.strategy_models import EURUSDConfluenceScore


class EURUSDConfluenceEngine:
    """Combine EURUSD strategy contexts into final confidence and trade quality."""

    MAX_RAW_SCORE = 205.0

    def score(
        self,
        session_context: Any,
        indicator_context: Any,
        liquidity_context: Any,
        structure_context: Any,
        fvg_context: Any,
        order_block_context: Any,
        regime_context: Any,
        news_context: Any | None = None,
        macro_context: Any | None = None,
    ) -> EURUSDConfluenceScore:
        score = EURUSDConfluenceScore()
        aligned: list[str] = []
        missing: list[str] = []
        warnings: list[str] = []

        score.session_score = self._session_score(session_context, aligned, missing)
        score.indicator_score = self._indicator_score(indicator_context, aligned, missing)
        score.liquidity_score = self._liquidity_score(liquidity_context, aligned, missing)
        score.structure_score = self._structure_score(structure_context, aligned, missing)
        score.fvg_score = self._fvg_score(fvg_context, aligned, missing)
        score.order_block_score = self._order_block_score(order_block_context, aligned, missing)
        score.regime_score = self._regime_score(regime_context, aligned, missing, warnings)
        score.news_score = self._news_score(news_context, aligned, missing, warnings)
        score.macro_score = self._macro_score(macro_context, aligned, missing, warnings)
        score.total_score = round(
            score.session_score
            + score.indicator_score
            + score.liquidity_score
            + score.structure_score
            + score.fvg_score
            + score.order_block_score
            + score.regime_score
            + score.news_score
            + score.macro_score,
            2,
        )

        confidence = round(min((score.total_score / self.MAX_RAW_SCORE) * 100, 100.0), 2)
        confidence = self._apply_caps(
            confidence,
            session_context,
            liquidity_context,
            structure_context,
            fvg_context,
            order_block_context,
            regime_context,
            news_context,
            warnings,
        )
        score.confidence = confidence
        score.trade_quality = self._trade_quality(confidence)
        score.risk_mode = self._risk_mode(score.trade_quality, regime_context)

        if self._get(regime_context, "risk_mode", "NO_TRADE") == "NO_TRADE":
            score.confidence = min(score.confidence, 20.0)
            score.trade_quality = "NO_TRADE"
            score.risk_mode = "NO_TRADE"
            warnings.append("EURUSD regime risk mode is NO_TRADE; confluence is hard-blocked.")
        if self._news_blocks(news_context):
            score.confidence = 0.0
            score.trade_quality = "NO_TRADE"
            score.risk_mode = "NO_TRADE"
            warnings.append("EURUSD news context blocks signal confidence.")

        score.aligned_confirmations = aligned
        score.missing_confirmations = missing
        score.warnings = warnings
        return score

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
            aligned.append("EURUSD liquidity sweep")
        else:
            missing.append("EURUSD liquidity sweep")
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

    def _structure_score(self, structure_context: Any, aligned: list[str], missing: list[str]) -> float:
        score = 0.0
        if self._has_structure_shift(structure_context):
            score += 20.0
            aligned.append("BOS/CHOCH structure shift")
        else:
            missing.append("BOS/CHOCH structure shift")
        if self._get(structure_context, "post_sweep_confirmation", False):
            score += 15.0
            aligned.append("Post-sweep structure confirmation")
        else:
            missing.append("Post-sweep structure confirmation")
        if self._get(structure_context, "structure_quality", "NONE") == "HIGH":
            score += 10.0
            aligned.append("High-quality structure")
        else:
            missing.append("High-quality structure")
        return score

    def _fvg_score(self, fvg_context: Any, aligned: list[str], missing: list[str]) -> float:
        latest = self._get(fvg_context, "latest_fvg", None)
        active_aligned = bool(self._get(fvg_context, "active_fvg_detected", False)) and latest is not None and (
            self._get(latest, "aligned_with_structure", False) or self._get(latest, "aligned_with_liquidity", False)
        )
        score = 0.0
        if active_aligned:
            score += 15.0
            aligned.append("Active aligned FVG")
        else:
            missing.append("Active aligned FVG")
        if self._get(fvg_context, "fvg_quality", "NONE") == "HIGH":
            score += 10.0
            aligned.append("High-quality FVG")
        else:
            missing.append("High-quality FVG")
        return score

    def _order_block_score(self, order_block_context: Any, aligned: list[str], missing: list[str]) -> float:
        latest = self._get(order_block_context, "latest_order_block", None)
        active_aligned = bool(self._get(order_block_context, "active_order_block_detected", False)) and latest is not None and (
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
        if self._get(regime_context, "regime", "UNCLEAR") == "TRENDING":
            score += 15.0
            aligned.append("Trending regime")
        else:
            missing.append("Trending regime")
        if self._get(regime_context, "tradeability", "AVOID") == "HIGH":
            score += 10.0
            aligned.append("High regime tradeability")
        else:
            missing.append("High regime tradeability")
        if self._get(regime_context, "risk_mode", "NO_TRADE") == "NO_TRADE":
            warnings.append("NO_TRADE regime detected.")
        return score

    def _news_score(self, news_context: Any | None, aligned: list[str], missing: list[str], warnings: list[str]) -> float:
        if news_context is None:
            missing.append("News risk context")
            return 0.0
        action = self._get(news_context, "trade_action", "ALLOW")
        risk = self._get(news_context, "risk_level", "LOW")
        if self._get(news_context, "high_impact_event_active", False) or action == "BLOCK":
            warnings.append("High-impact news context blocks EURUSD confluence.")
            return -50.0
        if action == "REDUCE_RISK" or risk == "MEDIUM":
            warnings.append("Medium news risk reduces EURUSD confluence.")
            return -10.0
        aligned.append("Clear news risk context")
        return 5.0

    def _macro_score(self, macro_context: Any | None, aligned: list[str], missing: list[str], warnings: list[str]) -> float:
        if macro_context is None:
            missing.append("Macro/DXY context")
            return 0.0
        alignment = self._get(macro_context, "macro_alignment", "UNKNOWN")
        adjustment = float(self._get(macro_context, "confidence_adjustment", 0.0) or 0.0)
        if alignment == "ALIGNED" or adjustment > 0:
            aligned.append("Macro/DXY alignment")
            return 10.0
        if alignment == "CONFLICTING" or adjustment < 0:
            warnings.append("Macro/DXY context conflicts with EURUSD direction.")
            return -15.0
        missing.append("Macro/DXY alignment")
        return 0.0

    def _apply_caps(
        self,
        confidence: float,
        session_context: Any,
        liquidity_context: Any,
        structure_context: Any,
        fvg_context: Any,
        order_block_context: Any,
        regime_context: Any,
        news_context: Any | None,
        warnings: list[str],
    ) -> float:
        capped = confidence
        if self._get(liquidity_context, "sweep_direction", "NONE") == "NONE":
            capped = min(capped, 40.0)
            warnings.append("Confidence capped at 40 because no liquidity sweep is present.")
        if not self._has_structure_shift(structure_context):
            capped = min(capped, 50.0)
            warnings.append("Confidence capped at 50 because no BOS/CHOCH is present.")
        if not self._get(fvg_context, "active_fvg_detected", False) and not self._get(order_block_context, "active_order_block_detected", False):
            capped = min(capped, 60.0)
            warnings.append("Confidence capped at 60 because no active FVG or order block is present.")
        if self._get(session_context, "session_quality", "LOW") == "LOW":
            capped = min(capped, 50.0)
            warnings.append("Confidence capped at 50 because session quality is LOW.")
        if self._get(regime_context, "risk_mode", "NO_TRADE") == "NO_TRADE":
            capped = min(capped, 20.0)
        if self._news_blocks(news_context):
            capped = 0.0
        return round(max(0.0, capped), 2)

    def _news_blocks(self, news_context: Any | None) -> bool:
        if news_context is None:
            return False
        return bool(self._get(news_context, "high_impact_event_active", False)) or self._get(news_context, "trade_action", "ALLOW") == "BLOCK"

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

    def _has_structure_shift(self, structure_context: Any) -> bool:
        return self._get(structure_context, "bos_direction", "NONE") != "NONE" or self._get(structure_context, "choch_direction", "NONE") != "NONE"

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
