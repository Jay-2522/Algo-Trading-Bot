from typing import Any

from backend.institutional_intelligence.break_even_manager import BreakEvenManager
from backend.institutional_intelligence.emergency_risk_exit import EmergencyRiskExit
from backend.institutional_intelligence.paper_trade_context_builder import PaperTradeContextBuilder
from backend.institutional_intelligence.paper_trade_models import PaperTradeLifecycleContext, PaperTradePosition
from backend.institutional_intelligence.partial_take_profit_manager import PartialTakeProfitManager
from backend.institutional_intelligence.position_management_models import (
    EmergencyExitSignal,
    InstitutionalPositionManagement,
    ManagedPosition,
    ManagementDecision,
    PositionState,
)
from backend.institutional_intelligence.position_state_machine import PositionStateMachine
from backend.institutional_intelligence.session_exit_manager import SessionExitManager
from backend.institutional_intelligence.structural_exit_detector import StructuralExitDetector
from backend.institutional_intelligence.trailing_stop_manager import TrailingStopManager


class PositionManagementContextBuilder:
    """Manage active paper positions without creating any execution side effect."""

    def __init__(
        self,
        paper_trade_builder: PaperTradeContextBuilder | None = None,
        partial_manager: PartialTakeProfitManager | None = None,
        break_even_manager: BreakEvenManager | None = None,
        trailing_manager: TrailingStopManager | None = None,
        structural_exit_detector: StructuralExitDetector | None = None,
        session_exit_manager: SessionExitManager | None = None,
        emergency_risk_exit: EmergencyRiskExit | None = None,
        state_machine: PositionStateMachine | None = None,
    ) -> None:
        self.paper_trade_builder = paper_trade_builder or PaperTradeContextBuilder()
        self.partial_manager = partial_manager or PartialTakeProfitManager()
        self.break_even_manager = break_even_manager or BreakEvenManager()
        self.trailing_manager = trailing_manager or TrailingStopManager()
        self.structural_exit_detector = structural_exit_detector or StructuralExitDetector()
        self.session_exit_manager = session_exit_manager or SessionExitManager()
        self.emergency_risk_exit = emergency_risk_exit or EmergencyRiskExit()
        self.state_machine = state_machine or PositionStateMachine()
        self._managed: dict[str, ManagedPosition] = {}

    def build_position_management_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        paper_context: PaperTradeLifecycleContext | None = None,
        structure_context: Any = None,
        breaker_context: Any = None,
        session_context: Any = None,
        risk_context: Any = None,
        simulation_integrity: bool = True,
    ) -> InstitutionalPositionManagement:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        paper = paper_context or self.paper_trade_builder.build_paper_trade_context(
            normalized_symbol, normalized_timeframe, candles
        )
        decisions: list[ManagementDecision] = []
        partials = []
        break_even_adjustments = []
        trailing_adjustments = []
        structural_signals = []
        session_reasons: list[str] = []
        latest_state: PositionState | None = None
        emergency = EmergencyExitSignal(triggered=False, shutdown_reason="No active simulated position to evaluate.")

        active_paper = list(paper.active_positions)
        if not active_paper:
            decisions.append(
                ManagementDecision(action="NO_POSITION", reason="No active paper position requires management.")
            )
            return InstitutionalPositionManagement(
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
                decisions=decisions,
                emergency_exit=emergency,
                management_status="NO_POSITION",
                summary="No active simulated position is available for institutional management.",
            )

        for paper_position in active_paper:
            managed = self._managed.get(paper_position.position_id) or self._from_paper_position(
                paper_position, normalized_timeframe
            )
            emergency = self.emergency_risk_exit.evaluate_emergency(
                managed,
                risk_context=risk_context,
                structure_context=structure_context,
                candles=candles,
                simulation_integrity=simulation_integrity,
            )
            if emergency.triggered:
                managed, latest_state = self.state_machine.transition(
                    managed, "EMERGENCY_EXIT", emergency.shutdown_reason
                )
                decisions.append(
                    ManagementDecision(
                        position_id=managed.position_id,
                        action="EMERGENCY_EXIT",
                        state=managed.state,
                        reason=emergency.shutdown_reason,
                        confidence=100.0,
                    )
                )
                self._managed[managed.position_id] = managed
                continue

            structural = self.structural_exit_detector.detect_exit(managed, structure_context, breaker_context)
            structural_signals.append(structural)
            if structural.exit_required:
                managed, latest_state = self.state_machine.transition(
                    managed, "INVALIDATED", structural.exit_reason
                )
                decisions.append(
                    ManagementDecision(
                        position_id=managed.position_id,
                        action="EXIT_SIMULATION",
                        state=managed.state,
                        reason=structural.exit_reason,
                        confidence=structural.confidence,
                    )
                )
                self._managed[managed.position_id] = managed
                continue

            session_exit = self.session_exit_manager.evaluate_exit(managed, session_context)
            if session_exit is not None:
                managed, latest_state = self.state_machine.transition(managed, "CLOSING", session_exit.reason)
                decisions.append(session_exit.model_copy(update={"state": managed.state}))
                session_reasons.append(session_exit.reason)
                self._managed[managed.position_id] = managed
                continue

            managed, position_partials = self.partial_manager.evaluate(managed, candles)
            partials.extend(position_partials)
            if any(partial.level == "TP1" for partial in position_partials) and managed.state == "ACTIVE":
                managed, latest_state = self.state_machine.transition(managed, "PARTIAL_TP_1", "TP1 realized at 1R.")
            if managed.tp1_achieved and managed.state == "PARTIAL_TP_1":
                managed, break_even = self.break_even_manager.apply_break_even(managed)
                break_even_adjustments.append(break_even)
                managed, latest_state = self.state_machine.transition(managed, "BREAK_EVEN", break_even.reason)
            if managed.break_even_applied and managed.state == "BREAK_EVEN":
                managed, latest_state = self.state_machine.transition(
                    managed, "TRAILING", "Runner eligible for structure-aware trailing."
                )
            if any(partial.level == "TP2" for partial in position_partials) and managed.state == "TRAILING":
                managed, latest_state = self.state_machine.transition(managed, "PARTIAL_TP_2", "TP2 realized at 2R.")
            managed, trailing = self.trailing_manager.adjust_stop(managed, candles, structure_context)
            if trailing.applied:
                trailing_adjustments.append(trailing)
                decisions.append(
                    ManagementDecision(
                        position_id=managed.position_id,
                        action="TRAIL_STOP",
                        state=managed.state,
                        reason=trailing.reason,
                        confidence=80.0,
                    )
                )
            elif position_partials:
                decisions.append(
                    ManagementDecision(
                        position_id=managed.position_id,
                        action="PARTIAL_TAKE_PROFIT",
                        state=managed.state,
                        reason="Simulated partial profit milestones were recorded and runner protection evaluated.",
                        confidence=85.0,
                    )
                )
            else:
                decisions.append(
                    ManagementDecision(
                        position_id=managed.position_id,
                        action="HOLD",
                        state=managed.state,
                        reason="Position remains within protected institutional management conditions.",
                        confidence=70.0,
                    )
                )
            self._managed[managed.position_id] = managed

        managed_positions = [self._managed[position.position_id] for position in active_paper if position.position_id in self._managed]
        active = [
            position for position in managed_positions
            if position.state not in {"CLOSED", "INVALIDATED", "EMERGENCY_EXIT"}
        ]
        if emergency.triggered:
            status = "EMERGENCY"
        elif any(position.state == "INVALIDATED" for position in managed_positions) or session_reasons:
            status = "EXIT_REQUIRED"
        elif partials or trailing_adjustments or break_even_adjustments:
            status = "MANAGING"
        else:
            status = "ACTIVE"
        return InstitutionalPositionManagement(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            managed_positions=managed_positions,
            active_positions=active,
            decisions=decisions,
            partial_take_profits=partials,
            break_even_adjustments=break_even_adjustments,
            trailing_stop_adjustments=trailing_adjustments,
            structural_exit_signals=structural_signals,
            emergency_exit=emergency,
            session_exit_reasons=session_reasons,
            latest_state=latest_state,
            management_status=status,
            summary=self._summary(status, managed_positions),
        )

    def _from_paper_position(self, position: PaperTradePosition, timeframe: str) -> ManagedPosition:
        risk = abs(position.entry_price - position.invalidation_level)
        if risk <= 0:
            risk = 0.00000001
        return ManagedPosition(
            position_id=position.position_id,
            candidate_id=position.candidate_id,
            symbol=position.symbol,
            timeframe=timeframe,
            direction=position.direction,
            entry_price=position.entry_price,
            initial_stop=position.invalidation_level,
            current_stop=position.invalidation_level,
            target_level=position.target_level,
            initial_risk=risk,
            opened_at=position.opened_at,
            metadata=dict(position.metadata),
        )

    def _summary(self, status: str, positions: list[ManagedPosition]) -> str:
        if status == "EMERGENCY":
            return "Emergency paper-position exit required; no live execution action is authorized."
        if status == "EXIT_REQUIRED":
            return "An institutional exit condition requires simulated position closure."
        if status == "MANAGING":
            return "Paper positions are under active profit-protection and runner management."
        return f"{len(positions)} paper position(s) remain active under institutional management."
