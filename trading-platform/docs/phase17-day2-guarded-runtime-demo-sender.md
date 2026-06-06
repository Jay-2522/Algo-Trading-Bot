# Phase 17 Day 2 Guarded Runtime Demo Sender

## Safety Gates

The guarded runtime sender calls MT5 only when every gate passes:

- `environment = DEMO`
- `symbol = EURUSD`
- `action = BUY` or `SELL`
- `lot = 0.01`
- manual confirmation and all acknowledgements are true
- `execute_single_demo_order_now = true`
- latest approval workflow is approved
- final approval is approved for one future demo test
- dry-run, preflight, simulator, and readiness are complete
- MT5 account is connected and confirmed DEMO by server name or trade mode
- live and production broker execution remain disabled
- SL and TP are provided
- no prior guarded demo send attempt exists

## MT5 Order Request

For `BUY`, the sender uses the current MT5 ask and `mt5.ORDER_TYPE_BUY`.

For `SELL`, the sender uses the current MT5 bid and `mt5.ORDER_TYPE_SELL`.

The request uses:

- `symbol = EURUSD`
- `volume = 0.01`
- `sl = payload stop_loss`
- `tp = payload take_profit`
- `deviation = 20`
- `magic = 17001`
- `comment = PHASE17_SINGLE_DEMO_TEST`

## One-Trade Limit

After one guarded send attempt, whether accepted or rejected by MT5, `demo_send_attempted` becomes true. Further send attempts are rejected with `SINGLE_TRADE_LIMIT_REACHED`.

## No Live Trading

The sender rejects live/production execution flags and validates a DEMO account before any runtime MT5 call.

## Verify Result

Run:

```powershell
python tests\phase17_day2_guarded_runtime_sender_verification.py
```

The verification script does not send a real order. It validates route availability, rejection behavior, missing final flag behavior, scoped `mt5.order_send` placement, and safety flags.
