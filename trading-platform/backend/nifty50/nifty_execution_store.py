from backend.nifty50.nifty_execution_models import NIFTYExecutionAuditEvent, NIFTYExecutionIntent, NIFTYOrderPreview


class NIFTYExecutionStore:
    def __init__(self) -> None:
        self._intents: list[NIFTYExecutionIntent] = []
        self._previews: list[NIFTYOrderPreview] = []
        self._audit_events: list[NIFTYExecutionAuditEvent] = []

    def store_intent(self, intent: NIFTYExecutionIntent) -> NIFTYExecutionIntent:
        self._intents.append(intent)
        return intent

    def list_intents(self, limit: int = 100) -> list[NIFTYExecutionIntent]:
        return self._intents[-limit:]

    def get_intent(self, intent_id: str) -> NIFTYExecutionIntent | None:
        return next((intent for intent in self._intents if intent.intent_id == intent_id), None)

    def store_preview(self, preview: NIFTYOrderPreview) -> NIFTYOrderPreview:
        self._previews.append(preview)
        return preview

    def list_previews(self, limit: int = 100) -> list[NIFTYOrderPreview]:
        return self._previews[-limit:]

    def get_preview(self, preview_id: str) -> NIFTYOrderPreview | None:
        return next((preview for preview in self._previews if preview.preview_id == preview_id), None)

    def store_audit_event(self, event: NIFTYExecutionAuditEvent) -> NIFTYExecutionAuditEvent:
        self._audit_events.append(event)
        return event

    def list_audit_events(self, limit: int = 100) -> list[NIFTYExecutionAuditEvent]:
        return self._audit_events[-limit:]
