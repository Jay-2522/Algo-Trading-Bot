from backend.deployment.deployment_models import DeploymentReadinessStatus


class DeploymentHealthStore:
    """In-memory store for latest deployment readiness checks."""

    _latest_status: DeploymentReadinessStatus | None = None
    _history: list[DeploymentReadinessStatus] = []

    def store_status(self, status: DeploymentReadinessStatus) -> DeploymentReadinessStatus:
        self._latest_status = status
        self._history.insert(0, status)
        del self._history[100:]
        return status

    def latest_status(self) -> DeploymentReadinessStatus | None:
        return self._latest_status

    def history(self, limit: int = 20) -> list[DeploymentReadinessStatus]:
        return self._history[: max(1, min(int(limit), 100))]
