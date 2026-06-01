from datetime import datetime, timezone


class SystemMetrics:
    """Collect system metrics with psutil when available."""

    def get_metrics(self) -> dict:
        try:
            import psutil

            return {
                "cpu_percent": psutil.cpu_percent(interval=0.0),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage(".").percent,
                "process_count": len(psutil.pids()),
                "timestamp": datetime.now(timezone.utc),
                "metrics_available": True,
                "warnings": [],
            }
        except Exception:
            return {
                "cpu_percent": None,
                "memory_percent": None,
                "disk_percent": None,
                "process_count": None,
                "timestamp": datetime.now(timezone.utc),
                "metrics_available": False,
                "warnings": ["psutil is unavailable; returning safe placeholder metrics."],
            }
