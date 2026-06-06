# Phase 18 Roadmap

## Day 1 - First Demo Order Result Capture

Capture the guarded MT5 demo sender result for the first approved EURUSD 0.01 lot runtime order attempt. Record ticket, retcode, server, account login, and rejection comments if MT5 rejects.

## Day 2 - Trade Journal Lifecycle Tracking

Persist the demo trade lifecycle from planned/sent through open/closed states using the persistent trade journal. Keep unknown values empty until verified from the demo account.

## Day 3 - MT5 Open-Position Monitoring

Read MT5 demo open-position data for the approved ticket and reconcile it with the journal. Do not send additional orders.

## Day 4 - Trade Closure Tracking

Record closure details after the demo trade closes, including close price, profit/loss, result, and MT5 comments where available.

## Day 5 - Dashboard/Report Sync

Verify the dashboard, Strategy Analytics, and Reports V2 reflect the persistent journal without fake trades, fake win rate, or fake P&L.

## Day 6 - Copier Simulation Using Real Demo Signal

Use the recorded demo signal to simulate copier queue creation only. No copier account execution, MT5 order send, or broker API call is allowed.

## Day 7 - Demo Execution Summary And Readiness Review

Summarize the single demo execution lifecycle, reporting accuracy, journal integrity, copier simulation output, blockers, and readiness for any future controlled demo execution phase.
