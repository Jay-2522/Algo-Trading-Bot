from backend.broker_integrations.mt5.mt5_client import MT5Client
from backend.utils.logger import get_logger


logger = get_logger(__name__)


def main() -> None:
    client = MT5Client()

    try:
        client.connect()
        account_info = client.get_account_info()
        xauusd_info = client.get_symbol_info("XAUUSD")
        latest_tick = client.get_latest_tick("XAUUSD")

        print("MT5 connection test: PASS")
        print(f"Account: {getattr(account_info, 'login', 'unknown')}")
        print(f"XAUUSD visible: {getattr(xauusd_info, 'visible', 'unknown')}")
        print(f"XAUUSD latest tick: {latest_tick}")
    except Exception as exc:
        print("MT5 connection test: FAIL")
        print(f"Helpful error: {exc}")
        print("Confirm MetaTrader 5 terminal is installed, running, logged in, and the MetaTrader5 Python package is installed.")
        logger.exception("MT5 connection test failed")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

