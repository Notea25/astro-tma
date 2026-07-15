# Load testing and profiling

Run load tests against local or staging environments first. The scripts reject
non-loopback targets unless remote execution is explicitly enabled. Never point
them at production without a test window, monitoring, rollback criteria, and an
agreed traffic ceiling.

## 1. Fast dependency-free probe

The local Compose backend is normally exposed on port `8018`:

```bash
python3 scripts/load_test_async.py \
  --base http://127.0.0.1:8018 \
  --path /health \
  -n 2000 -c 50 \
  --expect 200
```

The expected status is part of the assertion. For example, with auth bypass
disabled, this probes the unauthenticated rejection path:

```bash
python3 scripts/load_test_async.py \
  --base http://127.0.0.1:8018 \
  --path /api/users/me \
  --method POST --body '{}' \
  -n 2000 -c 50 \
  --expect 401
```

This stdlib probe opens one TCP connection per request. Above roughly 100-200
concurrent requests on Docker Desktop, run the generator inside the Compose
network so host port-proxy limits are not mistaken for API failures.

## 2. Realistic signed Mini App launch

Start a disposable two-worker backend with real Telegram HMAC verification:

```bash
docker compose run -d --no-deps \
  --name astro-tma-load \
  -p 127.0.0.1:8019:8000 \
  -e APP_ENV=development \
  -e APP_DEBUG=false \
  -e AUTH_BYPASS=false \
  -e FEATURE_PUSH_NOTIFICATIONS=false \
  --entrypoint uvicorn backend \
  main:app --host 0.0.0.0 --port 8000 --workers 2
```

Run the battle profile. It deliberately performs `POST /api/users/me`, so use a
reserved ID range and remove those rows afterwards:

```bash
set -a
source .env
set +a
LOAD_BASE=http://127.0.0.1:8019 \
LOAD_USERS=500 \
LOAD_CONCURRENCY=100 \
LOAD_USER_BASE=9900000000 \
LOAD_MAX_ERROR_RATE=0 \
LOAD_MAX_P95_MS=750 \
python3 scripts/battle_load.py
```

The script aborts if signed IDs are replaced by the development auth-bypass
user. Set `LOAD_REQUIRE_DISTINCT_USERS=0` only when a same-user contention test
is intentional.

Clean up exactly the reserved range and stop the disposable backend:

```bash
docker exec astro-tma-postgres-1 \
  psql -v ON_ERROR_STOP=1 -U astro -d astro_tma \
  -c 'DELETE FROM users WHERE id BETWEEN 9900000000 AND 9900000499;'
docker rm -f astro-tma-load
```

To generate load from inside the Docker network, mount `battle_load.py` into the
backend image and target the disposable container by name. Because that target
is not loopback, also set `LOAD_ALLOW_REMOTE=1`.

## 3. CPU profiling

`pprof` is primarily a Go profiler. For this Python/FastAPI backend, use
`cProfile` for a dependency-free first pass or `py-spy` for lower-overhead
sampling. Do not compare cProfile throughput directly with an unprofiled run;
instrumentation intentionally slows Python calls.

Start a disposable cProfile backend:

```bash
docker compose run -d --no-deps \
  --name astro-tma-profile \
  -p 127.0.0.1:8019:8000 \
  -e APP_ENV=development \
  -e APP_DEBUG=false \
  -e AUTH_BYPASS=false \
  -e FEATURE_PUSH_NOTIFICATIONS=false \
  --entrypoint python backend \
  -m cProfile -o /tmp/profile.pstats \
  -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Run the signed profile from the previous section, then stop gracefully and read
the profile with the same Python image:

```bash
docker kill --signal=INT astro-tma-profile
docker wait astro-tma-profile
docker cp astro-tma-profile:/tmp/profile.pstats /tmp/astro-tma-profile.pstats
docker run --rm \
  -v /tmp/astro-tma-profile.pstats:/profile.pstats:ro \
  astro-tma-backend \
  python -c 'import pstats; pstats.Stats("/profile.pstats").strip_dirs().sort_stats("cumulative").print_stats(40)'
docker rm astro-tma-profile
rm /tmp/astro-tma-profile.pstats
```

During every load step, capture backend, PostgreSQL, and Redis resource usage:

```bash
docker stats --no-stream \
  astro-tma-load astro-tma-postgres-1 astro-tma-redis-1
```

Track at least request rate, p50/p95/p99, transport errors, HTTP 5xx, CPU, RSS,
DB connection count, and postflight health. Re-run the same scenario after any
optimization; change one variable at a time.
