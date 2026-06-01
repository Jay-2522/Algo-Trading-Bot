# Secrets Management Guide

## Required Placeholders

Committed env templates must contain:

- `ADMIN_API_KEY=API_KEY_PLACEHOLDER`
- `BROKER_LOGIN=BROKER_LOGIN_PLACEHOLDER`
- `BROKER_PASSWORD=BROKER_PASSWORD_PLACEHOLDER`
- `NEWS_API_KEY=NEWS_API_KEY_PLACEHOLDER`

## Production Env

Create `.env.production` locally on the VPS from `.env.production.example`.

Do not commit:

- `.env`
- `.env.local`
- `.env.production`
- API keys
- broker passwords
- account numbers
- private tokens

## Redaction

The config redactor returns `********` for keys containing:

- password
- secret
- token
- api_key
- login
- account
- private

## Safety Flags

Keep these values:

```env
SIMULATION_ONLY=true
DEMO_EXECUTION=true
LIVE_EXECUTION_ENABLED=false
BROKER_EXECUTION_ENABLED=false
```
