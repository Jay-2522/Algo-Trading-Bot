"use client";

import { useEffect, useRef, useState } from "react";

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
};

type Mt5PriceResponse = {
  bid?: number | string | null;
  ask?: number | string | null;
  marketOpen?: boolean;
  market_open?: boolean;
  symbol?: string;
  time?: string;
};

function isForexMarketOpen(): boolean {
  const now = new Date();
  const day = now.getUTCDay();
  const nowMin = now.getUTCHours() * 60 + now.getUTCMinutes();
  if (day === 6) return false;
  if (day === 0 && nowMin < 22 * 60) return false;
  if (day === 5 && nowMin >= 22 * 60) return false;
  return true;
}

function appendPoint(history: LivePricePoint[], price: number): LivePricePoint[] {
  return [...history, { time: Date.now(), value: price }].slice(-200);
}

function numeric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

export function useLivePrice(symbol: "EURUSD" | "XAUUSD"): LivePriceState {
  const [history, setHistory] = useState<LivePricePoint[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [marketOpen, setMarketOpen] = useState(() => isForexMarketOpen());
  const [endpointConnected, setEndpointConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Price data unavailable - backend endpoint /api/mt5/price not connected");
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      const fallbackMarketOpen = isForexMarketOpen();
      try {
        const response = await fetch(`/api/mt5/price?symbol=${symbol}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`MT5 price endpoint returned ${response.status}`);
        const payload = (await response.json()) as Mt5PriceResponse;
        const bid = numeric(payload.bid);
        const nextMarketOpen = typeof payload.marketOpen === "boolean" ? payload.marketOpen : typeof payload.market_open === "boolean" ? payload.market_open : fallbackMarketOpen;
        if (cancelled) return;
        setEndpointConnected(true);
        setMarketOpen(nextMarketOpen);
        setStatusMessage(nextMarketOpen ? "MT5 price feed connected" : "Market Closed");
        if (bid !== null) {
          setCurrentPrice(bid);
          if (nextMarketOpen) {
            setHistory((current) => appendPoint(current, bid));
          }
        }
      } catch {
        if (cancelled) return;
        setEndpointConnected(false);
        setMarketOpen(fallbackMarketOpen);
        setStatusMessage("Price data unavailable - backend endpoint /api/mt5/price not connected");
      } finally {
        if (!cancelled) {
          timerRef.current = window.setTimeout(poll, fallbackMarketOpen ? 5000 : 60000);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [symbol]);

  const previous = history.length > 1 ? history[history.length - 2].value : currentPrice;
  const delta = currentPrice !== null && previous !== null && marketOpen ? currentPrice - previous : 0;
  const deltaPercent = previous && currentPrice !== null && marketOpen ? (delta / previous) * 100 : 0;
  const direction = delta > 0 ? "up" : delta < 0 ? "down" : "flat";

  return { currentPrice, delta, deltaPercent, endpointConnected, history, marketOpen, direction, statusMessage };
}
