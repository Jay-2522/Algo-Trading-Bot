import os
import time


START_TIME = time.time()


class ProcessMonitor:
    """Report local backend/frontend process health without process control."""

    def get_process_status(self) -> dict:
        return {
            "backend_process": {
                "running": True,
                "pid": os.getpid(),
                "uptime_seconds": round(time.time() - START_TIME, 2),
                "warnings": [],
            },
            "frontend_process": {
                "running": None,
                "pid": None,
                "uptime_seconds": None,
                "warnings": ["Frontend process detection is not controlled by the backend runtime."],
            },
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
