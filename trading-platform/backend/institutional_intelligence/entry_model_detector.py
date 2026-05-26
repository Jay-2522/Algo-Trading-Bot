from typing import Any

from backend.institutional_intelligence.entry_model_models import InstitutionalEntryModel


class EntryModelDetector:
    """Detect candidate institutional entry patterns without creating execution intent."""

    def detect_entry_models(
        self,
        symbol: str,
        timeframe: str,
        sweep_context: Any = None,
        fvg_context: Any = None,
        order_block_context: Any = None,
        breaker_context: Any = None,
        structure_shift_context: Any = None,
        confluence_context: Any = None,
        alignment_context: Any = None,
        session_context: Any = None,
    ) -> list[InstitutionalEntryModel]:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        blocked = self._blocked(confluence_context, alignment_context, session_context)
        if blocked:
            return [self._no_trade(normalized_symbol, normalized_timeframe, blocked, session_context, alignment_context)]

        candidates: list[InstitutionalEntryModel] = []
        for direction in ("BULLISH", "BEARISH"):
            sweep = self._directional(self._items(sweep_context, "sweeps"), direction)
            fvg = self._directional(self._items(fvg_context, "fresh_fvgs"), direction)
            order_block = self._directional(self._items(order_block_context, "fresh_order_blocks"), direction)
            breaker = self._directional(self._items(breaker_context, "fresh_breakers"), direction)
            structure = self._structure(structure_shift_context, direction)
            aligned = self._supports_direction(confluence_context, alignment_context, direction)
            if sweep and fvg and self._not_opposed(structure_shift_context, direction):
                candidates.append(
                    self._candidate(
                        normalized_symbol,
                        normalized_timeframe,
                        "SWEEP_FVG_CONTINUATION",
                        direction,
                        fvg,
                        ["Validated liquidity sweep confirms the raid.", "Fresh fair value gap offers a retracement zone."],
                        sweep=sweep,
                        fvg=fvg,
                        structure=structure,
                        session=session_context,
                        alignment=alignment_context,
                    )
                )
            if order_block and aligned:
                candidates.append(
                    self._candidate(
                        normalized_symbol,
                        normalized_timeframe,
                        "ORDER_BLOCK_RETRACEMENT",
                        direction,
                        order_block,
                        ["Fresh order block is available.", "Directional confluence supports the retracement."],
                        order_block=order_block,
                        structure=structure,
                        session=session_context,
                        alignment=alignment_context,
                    )
                )
            if breaker and structure and aligned:
                candidates.append(
                    self._candidate(
                        normalized_symbol,
                        normalized_timeframe,
                        "BREAKER_RETEST",
                        direction,
                        breaker,
                        ["Fresh breaker block retest zone is available.", "Structure transition supports the breaker direction."],
                        breaker=breaker,
                        structure=structure,
                        session=session_context,
                        alignment=alignment_context,
                    )
                )
            if structure and self._get(structure, "event_type") == "MSS":
                zone = fvg or order_block or breaker
                if zone and (sweep or fvg) and self._alignment_not_opposed(alignment_context, direction):
                    candidates.append(
                        self._candidate(
                            normalized_symbol,
                            normalized_timeframe,
                            "MSS_REVERSAL",
                            direction,
                            zone,
                            ["Market structure shift confirms reversal intent.", "Directional imbalance or sweep supports reversal."],
                            sweep=sweep,
                            fvg=fvg,
                            order_block=order_block,
                            breaker=breaker,
                            structure=structure,
                            session=session_context,
                            alignment=alignment_context,
                        )
                    )
            if sweep and order_block and not fvg and aligned:
                candidates.append(
                    self._candidate(
                        normalized_symbol,
                        normalized_timeframe,
                        "LIQUIDITY_REVERSAL",
                        direction,
                        order_block,
                        ["Liquidity raid occurred.", "Fresh order block provides a reversal zone."],
                        sweep=sweep,
                        order_block=order_block,
                        structure=structure,
                        session=session_context,
                        alignment=alignment_context,
                    )
                )

        return candidates or [
            self._no_trade(
                normalized_symbol,
                normalized_timeframe,
                ["No qualified directional institutional entry pattern is present."],
                session_context,
                alignment_context,
            )
        ]

    def _candidate(
        self,
        symbol: str,
        timeframe: str,
        model_type: str,
        direction: str,
        zone: Any,
        factors: list[str],
        **related: Any,
    ) -> InstitutionalEntryModel:
        low, high = self._zone(zone)
        width = max((high or 0.0) - (low or 0.0), 0.0)
        invalidation = low - width if direction == "BULLISH" and low is not None else None
        target = high + (width * 2.0) if direction == "BULLISH" and high is not None else None
        if direction == "BEARISH" and high is not None:
            invalidation = high + width
            target = low - (width * 2.0) if low is not None else None
        return InstitutionalEntryModel(
            symbol=symbol,
            timeframe=timeframe,
            model_type=model_type,
            direction=direction,
            entry_zone_low=low,
            entry_zone_high=high,
            invalidation_level=invalidation,
            target_level=target,
            supporting_factors=factors,
            related_sweep=related.get("sweep"),
            related_fvg=related.get("fvg"),
            related_order_block=related.get("order_block"),
            related_breaker=related.get("breaker"),
            related_structure_event=related.get("structure"),
            session_context=related.get("session"),
            alignment_context=related.get("alignment"),
        )

    def _no_trade(
        self, symbol: str, timeframe: str, blocks: list[str], session: Any, alignment: Any
    ) -> InstitutionalEntryModel:
        return InstitutionalEntryModel(
            symbol=symbol,
            timeframe=timeframe,
            model_type="NO_TRADE",
            direction="NEUTRAL",
            readiness="AVOID" if any("block" in item.lower() or "conflict" in item.lower() for item in blocks) else "NO_SETUP",
            blocking_factors=blocks,
            warnings=blocks,
            session_context=session,
            alignment_context=alignment,
        )

    def _blocked(self, confluence: Any, alignment: Any, session: Any) -> list[str]:
        blocks = []
        score = self._get(confluence, "confluence_score")
        if self._get(score, "dominant_direction") == "CONFLICTED":
            blocks.append("Confluence direction is conflicted.")
        if self._get(score, "trade_readiness") == "BLOCKED_BY_RISK":
            blocks.append("Risk readiness blocks simulation.")
        if self._get(alignment, "overall_direction") == "CONFLICTED":
            blocks.append("Higher and lower timeframe alignment is conflicted.")
        if self._get(session, "trade_timing_readiness") in {"AVOID_NEWS_WINDOW", "AVOID_LOW_LIQUIDITY"}:
            blocks.append("Session or news timing blocks simulation.")
        return blocks

    def _supports_direction(self, confluence: Any, alignment: Any, direction: str) -> bool:
        score = self._get(confluence, "confluence_score")
        confluence_direction = self._get(score, "dominant_direction")
        alignment_direction = self._get(alignment, "overall_direction")
        return confluence_direction in {None, "NEUTRAL", direction} and alignment_direction in {None, "NEUTRAL", direction}

    def _alignment_not_opposed(self, alignment: Any, direction: str) -> bool:
        return self._get(alignment, "overall_direction") not in ({"BEARISH"} if direction == "BULLISH" else {"BULLISH"})

    def _not_opposed(self, context: Any, direction: str) -> bool:
        state = self._get(context, "current_structure_state")
        return state not in ({"BEARISH"} if direction == "BULLISH" else {"BULLISH"})

    def _structure(self, context: Any, direction: str) -> Any:
        events = [
            event for event in self._items(context, "events")
            if self._get(event, "direction") == direction and self._get(event, "valid") is not False
        ]
        return max(events, key=lambda event: float(self._get(event, "strength") or 0.0), default=None)

    def _directional(self, items: list[Any], direction: str) -> Any:
        valid = [
            item for item in items
            if self._get(item, "direction") == direction and self._get(item, "valid") is not False
        ]
        return max(valid, key=lambda item: float(self._get(item, "strength") or 0.0), default=None)

    def _zone(self, zone: Any) -> tuple[float | None, float | None]:
        low = self._get(zone, "gap_low")
        high = self._get(zone, "gap_high")
        if low is None or high is None:
            low, high = self._get(zone, "zone_low"), self._get(zone, "zone_high")
        return (float(low), float(high)) if low is not None and high is not None else (None, None)

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        return list((context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])) or [])

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
