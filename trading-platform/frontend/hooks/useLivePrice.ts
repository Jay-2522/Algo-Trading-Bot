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
};

const STARTING_PRICES: Record<string, number> = {
  EURUSD: 1.15654,
  XAUUSD: 2340.25,
};

const YAHOO_SYMBOLS: Record<string, string> = {
  EURUSD: "EURUSD=X",
  XAUUSD: "XAUUSD=X",
};

function appendPoint(history: LivePricePoint[], price: number): LivePricePoint[] {
  return [...history, { time: Date.now(), value: price }].slice(-200);
}

function simulatedPrice(symbol: string, previous: number | null): number {
  const base = STARTING_PRICES[symbol] ?? 1;
  const last = previous ?? base;
  const delta = symbol === "XAUUSD" ? (Math.random() - 0.5) * 1.8 : (Math.random() - 0.5) * 0.001;
  const min = base * 0.98;
  const max = base * 1.02;
  return Math.min(max, Math.max(min, Number((last + delta).toFixed(symbol === "XAUUSD" ? 2 : 5))));
}

export function useLivePrice(symbol: "EURUSD" | "XAUUSD"): LivePriceState {
  const [history, setHistory] = useState<LivePricePoint[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const lastPrice = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const pushPrice = (price: number) => {
      if (!Number.isFinite(price) || cancelled) return;
      lastPrice.current = price;
      setCurrentPrice(price);
      setHistory((current) => appendPoint(current, price));
    };

    const pollYahoo = async () => {
      try {
        const yahooSymbol = YAHOO_SYMBOLS[symbol];
        const response = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${yahooSymbol}?interval=1m&range=1d`);
        const payload = await response.json();
        const quote = payload?.chart?.result?.[0];
        const closes = quote?.indicators?.quote?.[0]?.close;
        const latest = Array.isArray(closes) ? closes.filter((value) => typeof value === "number").at(-1) : null;
        if (typeof latest === "number") {
          pushPrice(Number(latest.toFixed(symbol === "XAUUSD" ? 2 : 5)));
          return;
        }
        pushPrice(simulatedPrice(symbol, lastPrice.current));
      } catch {
        pushPrice(simulatedPrice(symbol, lastPrice.current));
      }
    };

    const seed = STARTING_PRICES[symbol];
    pushPrice(seed);
    const simInterval = window.setInterval(() => pushPrice(simulatedPrice(symbol, lastPrice.current)), 2000);
    const pollInterval = window.setInterval(() => void pollYahoo(), 10000);
    void pollYahoo();

    return () => {
      cancelled = true;
      window.clearInterval(simInterval);
      window.clearInterval(pollInterval);
    };
  }, [symbol]);

  const previous = history.length > 1 ? history[history.length - 2].value : currentPrice;
  const delta = currentPrice !== null && previous !== null ? currentPrice - previous : 0;
  const deltaPercent = previous && currentPrice !== null ? (delta / previous) * 100 : 0;
  const direction = delta > 0 ? "up" : delta < 0 ? "down" : "flat";

  return { currentPrice, delta, deltaPercent, history, direction };
}
