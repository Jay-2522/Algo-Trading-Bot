from __future__ import annotations

from datetime import datetime, timezone
import json

try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - host dependency
    mt5 = None
    IMPORT_ERROR = str(exc)
else:
    IMPORT_ERROR = ""


def main() -> int:
    if mt5 is None:
        print(json.dumps({"status": "UNAVAILABLE", "positions": [], "message": IMPORT_ERROR}))
        return 1
    initialized = False
    try:
        initialized = bool(mt5.initialize())
        if not initialized:
            print(json.dumps({"status": "NOT_CONNECTED", "positions": [], "message": f"MT5 initialize failed: {mt5.last_error()}"}))
            return 2
        account = mt5.account_info()
        raw = mt5.positions_get()
        if raw is None:
            print(json.dumps({"status": "READ_FAILED", "positions": [], "message": f"MT5 positions_get failed: {mt5.last_error()}"}))
            return 3
        positions = []
        for position in raw:
            side = "BUY" if int(getattr(position, "type", -1)) == int(getattr(mt5, "POSITION_TYPE_BUY", 0)) else "SELL"
            positions.append(
                {
                    "ticket": str(getattr(position, "ticket", "") or ""),
                    "symbol": str(getattr(position, "symbol", "") or "").upper(),
                    "type": side,
                    "side": side,
                    "volume": float(getattr(position, "volume", 0.0) or 0.0),
                    "lot": float(getattr(position, "volume", 0.0) or 0.0),
                    "price_open": float(getattr(position, "price_open", 0.0) or 0.0),
                    "entry_price": float(getattr(position, "price_open", 0.0) or 0.0),
                    "sl": float(getattr(position, "sl", 0.0) or 0.0),
                    "stop_loss": float(getattr(position, "sl", 0.0) or 0.0),
                    "tp": float(getattr(position, "tp", 0.0) or 0.0),
                    "take_profit": float(getattr(position, "tp", 0.0) or 0.0),
                    "price_current": float(getattr(position, "price_current", 0.0) or 0.0),
                    "current_price": float(getattr(position, "price_current", 0.0) or 0.0),
                    "profit": float(getattr(position, "profit", 0.0) or 0.0),
                    "floating_pnl": float(getattr(position, "profit", 0.0) or 0.0),
                    "time": int(getattr(position, "time", 0) or 0),
                    "comment": str(getattr(position, "comment", "") or ""),
                    "account_login": str(getattr(account, "login", "") or "") if account else "",
                    "server": str(getattr(account, "server", "") or "") if account else "",
                    "lifecycle_status": "OPEN",
                    "journal_status": "OPEN",
                }
            )
        print(
            json.dumps(
                {
                    "status": "POSITIONS_FOUND" if positions else "NO_OPEN_POSITIONS",
                    "positions": positions,
                    "positions_count": len(positions),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "MT5_ISOLATED_POSITION_PROBE",
                }
            )
        )
        return 0
    except Exception as exc:  # pragma: no cover - host dependency
        print(json.dumps({"status": "READ_FAILED", "positions": [], "message": str(exc)}))
        return 4
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
