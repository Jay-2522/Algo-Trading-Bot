class CopyDuplicateGuard:
    """In-memory guard for per-signal/account copy attempts."""

    def __init__(self) -> None:
        self._copied_keys: set[tuple[str, str, str, str]] = set()

    def is_duplicate(self, signal_id: str, account_id: str, symbol: str, action: str) -> bool:
        return self._key(signal_id, account_id, symbol, action) in self._copied_keys

    def mark_copied(self, signal_id: str, account_id: str, symbol: str, action: str) -> None:
        self._copied_keys.add(self._key(signal_id, account_id, symbol, action))

    def _key(self, signal_id: str, account_id: str, symbol: str, action: str) -> tuple[str, str, str, str]:
        return (str(signal_id), str(account_id), str(symbol).upper(), str(action).upper())
