from typing import Any


class SignalReasonBuilder:
    """Build client-readable and technical XAUUSD signal explanations."""

    def build_client_summary(self, signal: Any) -> str:
        if signal.action in {"BUY", "SELL"}:
            return (
                f"The bot found a {signal.action} candidate because liquidity, structure, entry-zone, "
                f"and regime confirmations are aligned. Execution remains disabled."
            )
        missing = self.build_missing_confirmation_text(signal.confluence_score)
        if missing:
            return f"The bot is waiting because {missing}."
        return "The bot is waiting because the full XAUUSD confirmation stack is not aligned yet."

    def build_technical_summary(self, contexts: dict[str, Any], score_breakdown: Any) -> str:
        liquidity = contexts["liquidity_context"]
        smc = contexts["smc_context"]
        regime = contexts["regime_context"]
        news = contexts.get("news_filter_decision")
        macro = contexts.get("macro_context")
        headline = contexts.get("headline_filter_decision")
        unified = contexts.get("unified_news_decision")
        news_text = ""
        if news is not None:
            news_text = (
                f" news_action={self._get(news, 'trade_action', 'ALLOW')} "
                f"news_blocked={self._get(news, 'blocked', False)};"
            )
        macro_text = ""
        if macro is not None:
            macro_text = (
                f" macro_bias={self._get(macro, 'gold_bias', 'UNKNOWN')} "
                f"macro_alignment={self._get(macro, 'macro_alignment', 'UNKNOWN')} "
                f"macro_adjustment={self._get(macro, 'confidence_adjustment', 0.0)};"
            )
        headline_text = ""
        if headline is not None:
            headline_text = (
                f" headline_action={self._get(headline, 'trade_action', 'ALLOW')} "
                f"headline_risk={self._get(headline, 'risk_level', 'LOW')} "
                f"headline_sentiment={self._get(headline, 'gold_sentiment', 'UNKNOWN')} "
                f"headline_blocked={self._get(headline, 'blocked', False)};"
            )
        unified_text = ""
        if unified is not None:
            unified_text = (
                f" unified_news_action={self._get(unified, 'final_trade_action', 'ALLOW')} "
                f"unified_news_risk={self._get(unified, 'final_risk_level', 'LOW')} "
                f"unified_news_cap={self._get(unified, 'confidence_cap', None)} "
                f"unified_news_adjustment={self._get(unified, 'confidence_adjustment', 0.0)};"
            )
        return (
            f"sweep={self._get(liquidity, 'sweep_direction', 'NONE')}; "
            f"bos={self._get(smc, 'bos_direction', 'NONE')}; "
            f"choch={self._get(smc, 'choch_direction', 'NONE')}; "
            f"fvg={self._get(smc, 'fvg_direction', 'NONE')} active={self._get(smc, 'active_fvg_detected', False)} "
            f"quality={self._get(smc, 'fvg_quality', 'NONE')}; "
            f"order_block={self._get(smc, 'order_block_direction', 'NONE')} active={self._get(smc, 'active_order_block_detected', False)} "
            f"quality={self._get(smc, 'order_block_quality', 'NONE')}; "
            f"regime={self._get(regime, 'regime', 'UNCLEAR')} tradeability={self._get(regime, 'tradeability', 'AVOID')}; "
            f"{news_text} "
            f"{macro_text} "
            f"{headline_text} "
            f"{unified_text} "
            f"confidence={self._get(score_breakdown, 'confidence', 0.0)}; "
            f"risk_mode={self._get(score_breakdown, 'risk_mode', 'NO_TRADE')}."
        )

    def build_missing_confirmation_text(self, score_breakdown: Any) -> str:
        missing = self._get(score_breakdown, "missing_confirmations", [])
        if not missing:
            return ""
        readable = [str(item).lower() for item in missing[:4]]
        if len(readable) == 1:
            return readable[0] + " is not confirmed yet"
        return ", ".join(readable[:-1]) + f", and {readable[-1]} are not confirmed yet"

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
