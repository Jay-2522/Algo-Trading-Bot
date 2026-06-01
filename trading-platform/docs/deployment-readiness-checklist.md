# Deployment Readiness Checklist

## VPS Location

- Recommended region: Mumbai.
- Preferred providers: Vultr Mumbai, AWS Mumbai, Contabo.
- Latency target: below 10ms ideal for broker connectivity.

## Python Backend

- Install Python 3.11+.
- Create and activate a virtual environment.
- Install backend dependencies with `pip install -r requirements.txt`.
- Start backend with `scripts/start_backend.ps1`.
- Backend should bind to `127.0.0.1:8000`.

## Node Frontend

- Install Node.js LTS.
- Run `npm install` inside `frontend`.
- Verify with `npm run build`.
- Start frontend with `scripts/start_frontend.ps1`.
- Frontend should bind to `127.0.0.1:3000`.

## MT5 Demo Terminal

- Install MetaTrader 5 on the VPS.
- Login only to a demo account.
- Live accounts remain blocked by platform policy.
- AutoTrading is required only for guarded demo execution tests.
- Do not enable any live execution flag.

## Environment Variables

- Configure `.env` or `.env.local`.
- Configure `frontend/.env.local`.
- Set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.
- Keep `simulation_only=true`.
- Keep `demo_execution=true`.
- Keep `live_execution_enabled=false`.
- Keep `broker_execution_enabled=false`.

## Ports

- Backend: `8000`.
- Frontend: `3000`.
- Use a reverse proxy only after local health checks pass.

## Logs

- Keep the `logs` directory present.
- Preserve `.gitkeep`.
- Ensure the VPS user can write application logs.

## Health Checks

- `GET /health`
- `GET /status`
- `GET /deployment/status`
- `GET /deployment/readiness`
- `GET /deployment/checklist`
- `GET /deployment/blockers`
- `GET /deployment/warnings`

## Safety Boundary

- Live trading disabled.
- Broker execution disabled.
- No autonomous trading.
- Demo execution only.
- No new MT5 order path.
- `mt5.order_send` must remain isolated to the existing guarded demo executor.
