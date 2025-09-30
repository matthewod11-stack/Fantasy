Runbook: Live Modes and Operational Safety

Purpose
-------
This runbook documents how to enable "live" integrations (HeyGen, TikTok,
OpenAI, Sleeper) in the Fantasy TikTok Engine, what secrets are required, how
we monitor runs, and common failure modes with remediation steps.

Enabling Live Mode
------------------
There are two orthogonal toggles:

- DRY_RUN: global development switch. When true, adapters return deterministic
  stubs and network calls are skipped.
- Service-specific LIVE toggles in `.env`:
  - HEYGEN_LIVE
  - TIKTOK_LIVE
  - OPENAI_ENABLED
  - SLEEPER_ENABLED

Defaults in `.env.example` are all false. To enable a live service in a
deployment, set the appropriate env var to `true` AND provide the required
secret credentials. Example (bash):

```bash
export DRY_RUN=false
export HEYGEN_LIVE=true
export HEYGEN_API_KEY="sk-..."
export TIKTOK_LIVE=true
export TIKTOK_CLIENT_KEY="..."
export TIKTOK_CLIENT_SECRET="..."
export TIKTOK_REDIRECT_URI="https://your-callback"
```

Required Secrets
----------------
- HeyGen: HEYGEN_API_KEY
- TikTok: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI
- OpenAI: OPENAI_API_KEY
- Google Sheets (optional tracking): GOOGLE_SHEETS_CREDENTIALS_PATH

Monitoring & Alerts
-------------------
- Logs: adapters emit structured JSON logs (packages.utils.logging). When a
  live adapter is constructed, it emits a conspicuous banner log entry.
  Search for "TIKTOK LIVE MODE ENABLED" or similar in your logging system to
  confirm a live run.
- Errors: runtime exceptions in live mode will fail fast (e.g., missing creds).
  Configure your orchestration (systemd / Kubernetes / GitHub Actions) to
  notify on non-zero exits from batch jobs.
- Rate-limits: client-side rate guards exist to reduce burst traffic. If you
  see 429s from providers, consider increasing backoff windows and reviewing
  batching.

Common Errors & Remediation
---------------------------
- Missing credentials
  - Symptom: Adapter construction raises "missing client_key/client_secret" or
    similar. Fix: populate the required env vars and retry.
- HeyGen uploads fail intermittently
  - Symptom: network errors / 5xx responses
  - Fix: retries/backoff are enabled client-side. If failures persist, check
    HeyGen service status and increase max attempts or contact HeyGen.
- TikTok auth token exchange returns unexpected shape
  - Symptom: "Unexpected token response" with token payload printed in logs
  - Fix: verify TOKEN_URL response with a curl request and ensure we have the
    right client credentials and redirect URI.
- Polling timeouts for HeyGen videos
  - Symptom: poll_status returns with note=poll_timeout
  - Fix: inspect upload sidecar (upload_id/video_id) and HeyGen dashboard. You
    can increase max poll attempts in code for problematic media.

Safety Checklist Before Enabling Live
-------------------------------------
- [ ] Secrets are stored securely (Vault/Secrets manager) and injected at
  deploy-time, not checked into git.
- [ ] DRY_RUN is explicitly set to `false` in the environment.
- [ ] Service-specific LIVE flags are enabled only for required services.
- [ ] Monitoring/alerting configured for job failures and 5xx/429 responses.

Developer Notes
---------------
- Default behavior remains DRY_RUN-friendly. Live mode must be opted into and
  will be noisy in logs and strict about the presence of secrets.
- Tests (`tests/test_adapters_live_flags.py`) validate that the default is
  dry-run and that live flips require credentials.

Contact
-------
For operational issues contact: ops@example.com
