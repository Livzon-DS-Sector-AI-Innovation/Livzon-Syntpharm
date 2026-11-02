# ADR-007: Require `REDIS_PASSWORD` in the UAT compose stack

## Status

Accepted — approved by the project owner on 2026-10-31.

## Context

`docker-compose.uat-infra.yml` and `docker-compose.uat.yml` referenced the Redis password as
`${REDIS_PASSWORD:-redis_uat_pwd}`. The fallback made the stack come up even when the variable
was missing, with a password that is written in a committed file. Two effects:

- Anyone with read access to the repository knows the UAT Redis credential, and the UAT Redis
  port `6379` is published on the host.
- A missing `.env.uat` entry fails silently into the default, so the difference between "set"
  and "not set" never surfaces until someone connects.

The audit flagged the edit as an infrastructure change with no approval record.

## Decision

Use `${REDIS_PASSWORD:?REDIS_PASSWORD 未设置}` in all three places (Redis `--requirepass`,
the healthcheck, and `REDIS_URL` for `backend` and `doc-gen-worker`). Compose now refuses to
start when the variable is absent, instead of starting with a published default.

`.env.uat.example` already documents the key:

```
REDIS_PASSWORD=<从团队获取>
REDIS_URL=redis://:<同一上面的密码>@uat-redis:6379/0
```

## Consequences

- Deploying UAT requires `REDIS_PASSWORD` in `.env.uat`. A missing value is a hard stop at
  `docker compose up` — loud, but it stops the stack rather than silently downgrading security.
- **Existing UAT `uat-data/redis` was created with the old password.** Redis stores the password
  in its config file, not in the AOF, so the running container keeps working after a restart with
  the same value. If the variable is changed, `uat-data/redis` must be recreated or the password
  rotated with `CONFIG SET requirepass`, otherwise the healthcheck fails.
- The default is gone from the repository; the credential now lives only in the deployment
  environment.
- Anyone deploying UAT from a checkout that predates this ADR must add the variable before
  pulling this change.