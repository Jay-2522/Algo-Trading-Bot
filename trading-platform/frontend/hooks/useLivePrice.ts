"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type LivePricePoint = {
  time: number;
  value: number;
};

export type LivePriceState = {
  currentPrice: number | null;
  delta: number;
  deltaPercent: number;
  history: LivePricePoint[];
  direction: "up" | "down" | "flat";
  marketOpen: boolean;
  endpointConnected: boolean;
  statusMessage: string;
  lastUpdated: string | null;
};

type LiveSymbol = "EURUSD" | "XAUUSD" | "NIFTY50";
type TickRecord = Record<string, unknown>;
type CachedLivePrice = {
  currentPrice: number | null;
  history: LivePricePoint[];
  lastUpdated: string | null;
  marketOpen: boolean;
  statusMessage: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const LIVE_POLL_INTERVAL_MS = 1000;
const CLOSED_POLL_INTERVAL_MS = 60000;
const STREAM_RECONNECT_MS = 2000;

function cacheKey(symbol: LiveSymbol): string {
  return `algopilot_live_price_${symbol}_v2`;
}

function buildTickUrl(symbol: LiveSymbol): string {
  const url = new URL(`/mt5-demo/market-data/tick/${symbol}`, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

function buildStreamUrl(symbol: LiveSymbol): string {
  const url = new URL(`/ws/market/${symbol}`, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

function isForexMarketOpen(): boolean {
  const now = new Date();
  const day = now.getUTCDay();
  const nowMin = now.getUTCHours() * 60 + now.getUTCMinutes();
  if (day === 6) return false;
  if (day === 0 && nowMin < 22 * 60) return false;
  if (day === 5 && nowMin >= 22 * 60) return false;
  return true;
}

function numericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.replace(/,/g, ""));
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function readNumeric(record: TickRecord | null | undefined, keys: string[]): number | null {
  for (const key of keys) {
    const value = numericValue(record?.[key]);
    if (value !== null) return value;
  }
  return null;
}

function extractPrice(record: TickRecord | null | undefined): number | null {
  const direct = readNumeric(record, ["last", "last_price", "ltp", "current_price", "price", "close", "bid_price", "ask_price", "value"]);
  if (direct !== null) return direct;
  const bid = readNumeric(record, ["bid"]);
  const ask = readNumeric(record, ["ask"]);
  if (bid !== null && ask !== null) return (bid + ask) / 2;
  return bid ?? ask;
}

function isSyntheticTick(record: TickRecord | null | undefined): boolean {
  const source = String(record?.source ?? record?.feed_source ?? "").toUpperCase();
  return source.includes("SIMULATION") || source.includes("FALLBACK") || source.includes("MOCK");
}

function readStatusText(record: TickRecord | null | undefined): string {
  return ["market_status", "feed_status", "status", "freshness", "state"]
    .map((key) => String(record?.[key] ?? "").toUpperCase())
    .filter(Boolean)
    .join(" ");
}

function inferMarketOpen(symbol: LiveSymbol, record: TickRecord | null | undefined, hasPrice: boolean): boolean {
  const explicit = record?.marketOpen ?? record?.market_open ?? record?.is_open ?? record?.open;
  if (typeof explicit === "boolean") return explicit;
  const status = readStatusText(record);
  if (/\b(CLOSED|MARKET_CLOSED|DISCONNECTED|OFFLINE|NO_FEED|STALE)\b/.test(status)) return false;
  if (/\b(MARKET_READY|READY|LIVE|OPEN|OK|ACTIVE)\b/.test(status) && hasPrice) return true;
  return symbol === "NIFTY50" ? false : isForexMarketOpen();
}

function appendPoint(history: LivePricePoint[], price: number): LivePricePoint[] {
  const last = history[history.length - 1];
  if (last && last.value === price) return history;
  return [...history, { time: Date.now(), value: price }].slice(-200);
}

function readCached(symbol: LiveSymbol): CachedLivePrice {
  if (typeof window === "undefined") {
    return { currentPrice: null, history: [], lastUpdated: null, marketOpen: symbol !== "NIFTY50" && isForexMarketOpen(), statusMessage: "Waiting for market feed" };
  }
  try {
    const raw = window.localStorage.getItem(cacheKey(symbol));
    if (!raw) throw new Error("No cache");
    const parsed = JSON.parse(raw) as Partial<CachedLivePrice>;
    return {
      currentPrice: numericValue(parsed.currentPrice) ?? null,
      history: Array.isArray(parsed.history) ? parsed.history.filter((point) => Number.isFinite(point?.value) && Number.isFinite(point?.time)) : [],
      lastUpdated: typeof parsed.lastUpdated === "string" ? parsed.lastUpdated : null,
      marketOpen: typeof parsed.marketOpen === "boolean" ? parsed.marketOpen : symbol !== "NIFTY50" && isForexMarketOpen(),
      statusMessage: typeof parsed.statusMessage === "string" ? parsed.statusMessage : "Last known market price",
    };
  } catch {
    return { currentPrice: null, history: [], lastUpdated: null, marketOpen: symbol !== "NIFTY50" && isForexMarketOpen(), statusMessage: "Waiting for market feed" };
  }
}

function writeCached(symbol: LiveSymbol, snapshot: CachedLivePrice): void {
  if (typeof window === "undefined" || snapshot.currentPrice === null) return;
  try {
    window.localStorage.setItem(cacheKey(symbol), JSON.stringify(snapshot));
  } catch {
    // Storage can be unavailable in private or restricted contexts.
  }
}

function messageFor(marketOpen: boolean, hasFreshPrice: boolean, hasCachedPrice: boolean): string {
  if (marketOpen && hasFreshPrice) return "MT5 live feed connected";
  if (!marketOpen && (hasFreshPrice || hasCachedPrice)) return "Market Closed";
  if (hasCachedPrice) return "Last known market price";
  return "Waiting for market feed";
}

export function useLivePrice(symbol: LiveSymbol, externalTick: TickRecord | null = null): LivePriceState {
  const [history, setHistory] = useState<LivePricePoint[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [marketOpen, setMarketOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Waiting for market feed");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const streamConnectedRef = useRef(false);
  const currentPriceRef = useRef<number | null>(null);
  const historyRef = useRef<LivePricePoint[]>([]);
  const lastUpdatedRef = useRef<string | null>(null);
  const marketOpenRef = useRef(false);

  useEffect(() => {
    const cached = readCached(symbol);
    setHistory(cached.history);
    setCurrentPrice(cached.currentPrice);
    setMarketOpen(cached.marketOpen);
    setStatusMessage(cached.statusMessage);
    setLastUpdated(cached.lastUpdated);
    historyRef.current = cached.history;
    currentPriceRef.current = cached.currentPrice;
    marketOpenRef.current = cached.marketOpen;
    lastUpdatedRef.current = cached.lastUpdated;
  }, [symbol]);

  const ingestTick = useCallback(
    (tick: TickRecord | null | undefined, fromPoll: boolean) => {
      const price = extractPrice(tick);
      const hasFreshPrice = price !== null && !isSyntheticTick(tick);
      const nextMarketOpen = inferMarketOpen(symbol, tick, hasFreshPrice);
      const previousPrice = currentPriceRef.current;
      const previousHistory = historyRef.current;
      const previousLastUpdated = lastUpdatedRef.current;
      const timestamp = typeof tick?.time === "string" ? tick.time : typeof tick?.timestamp === "string" ? tick.timestamp : hasFreshPrice ? new Date().toISOString() : previousLastUpdated;
      marketOpenRef.current = nextMarketOpen;
      setMarketOpen(nextMarketOpen);
      setStatusMessage(messageFor(nextMarketOpen, hasFreshPrice, previousPrice !== null));
      if (hasFreshPrice) {
        currentPriceRef.current = price;
        lastUpdatedRef.current = timestamp ?? null;
        setCurrentPrice(price);
        setLastUpdated(timestamp ?? null);
        setHistory((current) => {
          const nextHistory = appendPoint(current, price);
          historyRef.current = nextHistory;
          writeCached(symbol, {
            currentPrice: price,
            history: nextHistory,
            lastUpdated: timestamp ?? null,
            marketOpen: nextMarketOpen,
            statusMessage: messageFor(nextMarketOpen, true, true),
          });
          return nextHistory;
        });
      } else if (fromPoll && previousPrice !== null) {
        writeCached(symbol, {
          currentPrice: previousPrice,
          history: previousHistory,
          lastUpdated: previousLastUpdated,
          marketOpen: nextMarketOpen,
          statusMessage: messageFor(nextMarketOpen, false, true),
        });
      }
    },
    [symbol],
  );

  useEffect(() => {
    if (externalTick) ingestTick(externalTick, false);
  }, [externalTick, ingestTick]);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const response = await fetch(buildTickUrl(symbol), { cache: "no-store" });
        if (!response.ok) throw new Error(`MT5 tick endpoint returned ${response.status}`);
        const payload = (await response.json()) as TickRecord;
        if (!cancelled) ingestTick(payload, true);
      } catch {
        if (!cancelled) {
          setMarketOpen(symbol === "NIFTY50" ? false : isForexMarketOpen());
          setStatusMessage(currentPriceRef.current !== null ? "Last known market price" : "Waiting for market feed");
        }
      } finally {
        if (!cancelled) {
          const interval = marketOpenRef.current || symbol === "NIFTY50" ? LIVE_POLL_INTERVAL_MS : CLOSED_POLL_INTERVAL_MS;
          timerRef.current = window.setTimeout(poll, interval);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [ingestTick, symbol]);

  useEffect(() => {
    if (symbol === "NIFTY50") return;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      try {
        const socket = new WebSocket(buildStreamUrl(symbol));
        socketRef.current = socket;
        socket.onopen = () => {
          streamConnectedRef.current = true;
        };
        socket.onmessage = (event) => {
          try {
            ingestTick(JSON.parse(String(event.data)) as TickRecord, false);
          } catch {
            // Ignore malformed stream payloads and let polling keep the last valid price alive.
          }
        };
        socket.onclose = () => {
          streamConnectedRef.current = false;
          if (!cancelled) {
            reconnectRef.current = window.setTimeout(connect, STREAM_RECONNECT_MS);
          }
        };
        socket.onerror = () => {
          streamConnectedRef.current = false;
          socket.close();
        };
      } catch {
        streamConnectedRef.current = false;
        if (!cancelled) {
          reconnectRef.current = window.setTimeout(connect, STREAM_RECONNECT_MS);
        }
      }
    };

    connect();

    return () => {
      cancelled = true;
      streamConnectedRef.current = false;
      if (reconnectRef.current !== null) window.clearTimeout(reconnectRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [ingestTick, symbol]);

  const previous = history.length > 1 ? history[history.length - 2].value : currentPrice;
  const delta = currentPrice !== null && previous !== null ? currentPrice - previous : 0;
  const deltaPercent = previous && currentPrice !== null ? (delta / previous) * 100 : 0;
  const direction = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
  const endpointConnected = currentPrice !== null;

  return { currentPrice, delta, deltaPercent, endpointConnected, history, marketOpen, direction, statusMessage, lastUpdated };
}
