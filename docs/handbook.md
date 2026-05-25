# Engineering Handbook — Sample

## Deployment Process

All production deploys go through the staging environment first. Staging soak time is 60 minutes minimum before promotion. Hotfixes can skip soak only with on-call lead approval.

## Code Review

Every PR requires one approval. PRs touching billing, auth, or data-retention paths require two approvals — one of whom must be from the platform team.

## Postmortem Policy

Every P0 and P1 incident gets a written postmortem within 5 business days. Postmortems are blameless and published to the team wiki. Action items are tracked to closure.
