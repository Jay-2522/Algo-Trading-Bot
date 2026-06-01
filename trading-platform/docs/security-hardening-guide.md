# Security Hardening Guide

## Scope

Phase 10 Day 5 adds security readiness checks and access-policy classification. It does not enforce authentication yet and does not enable live trading.

## Rules

- Never commit real secrets.
- Keep production `.env` files outside source control.
- Use placeholders in committed templates.
- Protect admin/internal routes before client deployment.
- Keep live execution disabled.
- Keep broker execution disabled.

## Admin/Internal Routes

These are classified for future protection:

- `/deployment/*`
- `/monitoring/*`
- `/strategy-execution-bridge/*`
- `/trade-copier/*`
- `/execution-risk/*`
- `/demo-execution/*`
- `/control-center/*`

## Client-Safe Routes

- `/dashboard`
- `/strategy/analyze/*`
- `/news/status`
- `/deployment/status`

## VPS Firewall Recommendations Later

- Allow HTTP/HTTPS only through reverse proxy.
- Restrict backend port `8000` to localhost/private network.
- Restrict dashboard/admin access by IP allowlist where possible.
- Keep MT5 terminal access limited to the VPS operator.
