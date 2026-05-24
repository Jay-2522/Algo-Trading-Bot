from backend.database.persistence_service import PersistenceService


def seed_local_database() -> None:
    """Insert harmless local development seed records only."""

    service = PersistenceService()
    try:
        if not service.initialize_database():
            raise RuntimeError("Database initialization failed.")
        service.save_audit_log(
            {
                "component": "database.seed",
                "event_type": "LOCAL_SEED",
                "message": "Local development seed initialized.",
                "severity": "INFO",
                "metadata_json": {"safe": True},
            }
        )
        service.save_market_snapshot(
            {
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "bid": 0.0,
                "ask": 0.0,
                "spread": 0.0,
                "last_price": 0.0,
                "metadata_json": {"seed_record": True},
            }
        )
        print("Local database seed complete.")
    finally:
        service.close()


if __name__ == "__main__":
    seed_local_database()
