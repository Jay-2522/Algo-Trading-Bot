export type NormalizedStatus = "completed" | "pending" | "rejected" | "warning" | "info";

export type ActivityEvent = {
  id: string;
  category: string;
  title: string;
  detail: string;
  status: NormalizedStatus;
  timestamp: string | null;
};

export function readText(record: Record<string, unknown> | null | undefined, keys: string[], fallback = "Unknown"): string {
  for (const key of keys) {
    const value = record?.[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
  }
  return fallback;
}

export function readNumber(record: Record<string, unknown> | null | undefined, keys: string[], fallback = 0): number {
  for (const key of keys) {
    const value = record?.[key];
    if (typeof value === "number") {
      return value;
    }
  }
  return fallback;
}

export function normalizeStatus(value: unknown): NormalizedStatus {
  const text = String(value ?? "").toUpperCase();
  if (text.includes("REJECT") || text.includes("FAILED") || text.includes("BLOCK")) {
    return "rejected";
  }
  if (text.includes("WAIT") || text.includes("PEND") || text.includes("HELD") || text.includes("QUEUE")) {
    return "pending";
  }
  if (text.includes("WARN") || text.includes("PARTIAL")) {
    return "warning";
  }
  if (text.includes("VALID") || text.includes("READY") || text.includes("FILL") || text.includes("COMPLETE") || text.includes("SAFE")) {
    return "completed";
  }
  return "info";
}

export function formatRelativeTime(timestamp: string | null | undefined): string {
  if (!timestamp) {
    return "No timestamp";
  }
  const then = new Date(timestamp).getTime();
  if (Number.isNaN(then)) {
    return timestamp;
  }
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(timestamp).toLocaleString();
}

export function normalizeWebhookEvent(event: Record<string, unknown>): ActivityEvent {
  const status = readText(event, ["processing_status", "status"], "RECEIVED");
  return {
    id: readText(event, ["event_id", "signal_id"], crypto.randomUUID()),
    category: "Webhook",
    title: `${readText(event, ["symbol"], "Signal")} ${readText(event, ["action"], "ALERT")}`,
    detail: readText(event, ["source"], "TradingView webhook event"),
    status: normalizeStatus(status),
    timestamp: readText(event, ["timestamp"], ""),
  };
}

export function normalizeDecisionEvent(event: Record<string, unknown>): ActivityEvent {
  const decision = readText(event, ["final_decision", "routing_status"], "Decision");
  return {
    id: readText(event, ["decision_id", "signal_id"], crypto.randomUUID()),
    category: "Orchestration",
    title: `${readText(event, ["canonical_symbol"], "Signal")} ${decision}`,
    detail: readText(event, ["explanation", "risk_status", "institutional_status"], "Simulation-only orchestration decision"),
    status: normalizeStatus(decision),
    timestamp: readText(event, ["timestamp"], ""),
  };
}

export function normalizeQueueEvent(event: Record<string, unknown>): ActivityEvent {
  const intent = typeof event.intent === "object" && event.intent !== null ? (event.intent as Record<string, unknown>) : {};
  const status = readText(event, ["status", "readiness"], "QUEUED");
  return {
    id: readText(event, ["queue_id"], crypto.randomUUID()),
    category: "Queue",
    title: `${readText(intent, ["canonical_symbol"], "Queue item")} ${readText(intent, ["action"], "")}`,
    detail: readText(event, ["readiness"], "Execution queue preparation only"),
    status: normalizeStatus(status),
    timestamp: readText(event, ["created_at", "updated_at"], ""),
  };
}

export function normalizeAuditEvent(event: Record<string, unknown>): ActivityEvent {
  const eventType = readText(event, ["event_type"], "Lifecycle event");
  return {
    id: readText(event, ["event_id", "queue_id"], crypto.randomUUID()),
    category: "Lifecycle",
    title: eventType,
    detail: readText(event, ["message"], "Simulated lifecycle event"),
    status: normalizeStatus(eventType),
    timestamp: readText(event, ["timestamp"], ""),
  };
}

export function normalizeSecurityEvent(event: Record<string, unknown>): ActivityEvent {
  const eventType = readText(event, ["event_type"], "Security event");
  return {
    id: readText(event, ["event_id", "fingerprint"], crypto.randomUUID()),
    category: "Security",
    title: eventType,
    detail: readText(event, ["severity", "source_ip"], "Webhook security monitor"),
    status: normalizeStatus(eventType),
    timestamp: readText(event, ["timestamp"], ""),
  };
}
