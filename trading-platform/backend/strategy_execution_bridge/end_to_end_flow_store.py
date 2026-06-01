class EndToEndFlowStore:
    """In-memory audit store for Phase 9 end-to-end demo flow runs."""

    _flows: dict[str, object] = {}

    def store_flow(self, result):
        self._flows[result.flow_id] = result
        return result

    def list_flows(self, limit: int = 100) -> list:
        return sorted(self._flows.values(), key=lambda flow: flow.timestamp, reverse=True)[:limit]

    def get_flow(self, flow_id: str):
        return self._flows.get(flow_id)
