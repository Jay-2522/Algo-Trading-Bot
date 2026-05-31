from typing import Any


class EURUSDReasonBuilder:
    """Build client-readable and technical EURUSD signal explanations."""

    def build_client_summary(self, signal: Any) -> str:
        if signal.action in {"BUY", "SELL"}:
            return (
                f"EURUSD has a {signal.action} candidate because liquidity, structure, entry-zone, "
                "regime, and risk filters are aligned. Execution remains disabled."
            )
        missing = self.build_missing_confirmation_text(signal.confluence_score)
        if missing:
            return f"The bot is waiting because EURUSD {missing}."
        return "The bot is waiting because EURUSD liquidity, structure, and regime are not fully aligned."

    def build_technical_summary(self, contexts: dict[str, Any], score: Any) -> str:
        liquidity = contexts["liquidity_context"]
        structure = contexts["structure_context"]
        fvg = contexts["fvg_context"]
        order_block = contexts["order_block_context"]
        regime = contexts["regime_context"]
        news = contexts.get("news_context", {})
        macro = contexts.get("macro_context", {})
        return (
            f"sweep={self._get(liquidity, 'sweep_direction', 'NONE')}; "
            f"bos={self._get(structure, 'bos_direction', 'NONE')}; "
            f"choch={self._get(structure, 'choch_direction', 'NONE')}; "
            f"post_sweep={self._get(structure, 'post_sweep_confirmation', False)}; "
            f"fvg={self._get(fvg, 'fvg_direction', 'NONE')} active={self._get(fvg, 'active_fvg_detected', False)} "
            f"quality={self._get(fvg, 'fvg_quality', 'NONE')}; "
            f"order_block={self._get(order_block, 'order_block_direction', 'NONE')} active={self._get(order_block, 'active_order_block_detected', False)} "
            f"quality={self._get(order_block, 'order_block_quality', 'NONE')}; "
            f"regime={self._get(regime, 'regime', 'UNCLEAR')} tradeability={self._get(regime, 'tradeability', 'AVOID')} "
            f"risk_mode={self._get(regime, 'risk_mode', 'NO_TRADE')}; "
            f"news_action={self._get(news, 'trade_action', 'ALLOW')} news_risk={self._get(news, 'risk_level', 'LOW')}; "
            f"macro_alignment={self._get(macro, 'macro_alignment', 'UNKNOWN')} macro_adjustment={self._get(macro, 'confidence_adjustment', 0.0)}; "
            f"confidence={self._get(score, 'confidence', 0.0)}; "
            f"trade_quality={self._get(score, 'trade_quality', 'NO_TRADE')}; "
            f"risk_mode={self._get(score, 'risk_mode', 'NO_TRADE')}."
        )

    def build_missing_confirmation_text(self, score: Any) -> str:
        missing = self._get(score, "missing_confirmations", [])
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
