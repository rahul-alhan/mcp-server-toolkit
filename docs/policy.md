# Internal Knowledge Base — Sample Policy

## Data Retention

Operational logs are retained for 90 days. Customer-facing audit records are retained for 18 months. Aggregated analytics may be retained indefinitely once stripped of PII.

## Access Tiers

- **Tier 1 (read-only)**: support agents, customer success
- **Tier 2 (read/write)**: engineering, on-call
- **Tier 3 (admin)**: platform team only — all changes require two-person review

## Incident Severity

- **P0** — full outage, customer-impacting, page on-call immediately
- **P1** — degraded service for >5% of users; respond within 30 minutes
- **P2** — non-customer-facing; respond next business day
