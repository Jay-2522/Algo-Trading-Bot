class BrokerLotConstraints:
    """Validate broker-specific lot constraints using safe demo defaults."""

    DEFAULTS = {"min": 0.01, "max": 5.0, "step": 0.01}

    def validate_lot(self, broker_id: str, lot_size: float) -> tuple[bool, float, str | None]:
        constraints = self.DEFAULTS
        lot = max(0.0, float(lot_size or 0.0))
        if lot <= 0:
            return False, 0.0, "Lot size must be positive."
        if lot < constraints["min"]:
            return False, 0.0, f"Lot size below minimum {constraints['min']}."
        adjusted = min(lot, constraints["max"])
        step = constraints["step"]
        adjusted = round(round(adjusted / step) * step, 2)
        if adjusted < constraints["min"]:
            return False, 0.0, f"Adjusted lot below minimum {constraints['min']}."
        if adjusted < lot:
            return True, adjusted, f"Lot reduced to broker maximum {constraints['max']}."
        return True, adjusted, None
