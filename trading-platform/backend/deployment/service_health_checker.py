from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

from backend.deployment.runtime_models import RuntimeServiceStatus


class ServiceHealthChecker:
    """Read-only HTTP health checks for local runtime services."""

    BACKEND_URL = "http://127.0.0.1:8000/health"
    FRONTEND_URL = "http://localhost:3000/dashboard"

    def check_backend(self) -> RuntimeServiceStatus:
        return self._check("backend", 8000, self.BACKEND_URL)

    def check_frontend(self) -> RuntimeServiceStatus:
        return self._check("frontend", 3000, self.FRONTEND_URL)

    def check_all(self) -> dict:
        return {
            "backend": self.check_backend(),
            "frontend": self.check_frontend(),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _check(self, name: str, port: int, endpoint: str) -> RuntimeServiceStatus:
        try:
            request = Request(endpoint, method="GET", headers={"User-Agent": "deployment-runtime-check"})
            with urlopen(request, timeout=2) as response:
                running = 200 <= int(response.status) < 500
                status = "RUNNING" if running else "DEGRADED"
                warnings = [] if running else [f"{name} returned HTTP {response.status}."]
        except URLError as exc:
            running = False
            status = "STOPPED"
            warnings = [f"{name} health endpoint unavailable: {exc}"]
        except Exception as exc:
            running = False
            status = "UNKNOWN"
            warnings = [f"{name} health check failed safely: {exc}"]
        return RuntimeServiceStatus(
            service_name=name,
            running=running,
            port=port,
            health_endpoint=endpoint,
            last_health_check=datetime.now(timezone.utc),
            status=status,
            warnings=warnings,
        )
