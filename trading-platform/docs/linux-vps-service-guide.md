# Linux VPS Service Guide

## Recommendation

Use a Windows VPS for MT5 simplicity. Linux can run the backend and frontend, but MT5 generally requires Wine or a separate Windows host.

## Backend systemd Example

```ini
[Unit]
Description=Trading Platform Backend
After=network.target

[Service]
WorkingDirectory=/opt/trading-platform
ExecStart=/usr/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
Environment=SIMULATION_ONLY=true
Environment=DEMO_EXECUTION=true
Environment=LIVE_EXECUTION_ENABLED=false
Environment=BROKER_EXECUTION_ENABLED=false

[Install]
WantedBy=multi-user.target
```

## Frontend systemd Example

```ini
[Unit]
Description=Trading Platform Frontend
After=network.target

[Service]
WorkingDirectory=/opt/trading-platform/frontend
ExecStart=/usr/bin/npm run start
Restart=on-failure
Environment=NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

## Healthcheck

Use the same endpoints:

- `/health`
- `/deployment/runtime/status`
- `/monitoring/health`

## MT5 Note

If MT5 is required on Linux, use Wine only after manual testing. Windows VPS remains the recommended route for demo MT5 operations.
