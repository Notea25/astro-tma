"""Platform smoke checks via SSH."""
from __future__ import annotations

import json
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "194.99.21.53"
USER = "root"
KEY = __import__("os").path.expanduser("~/.ssh/astro_tma_deploy")
COMPOSE = "docker compose -f /opt/astro-tma/docker-compose.yml"


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> str:
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, key_filename=KEY, timeout=30)
    print("=== DOCKER PS ===")
    print(run(c, f"{COMPOSE} ps"))
    print("\n=== GIT REV ===")
    print(run(c, "cd /opt/astro-tma && git log -1 --oneline && git status -sb"))
    print("\n=== HEALTH LOCAL ===")
    print(run(c, "curl -s http://localhost:8000/health"))
    print("\n=== BACKEND LOGS (last 30) ===")
    print(run(c, "docker logs astro-tma-backend-1 --tail 30 2>&1"))
    print("\n=== WORKER LOGS (last 15) ===")
    print(run(c, "docker logs astro-tma-worker-1 --tail 15 2>&1"))
    print("\n=== REDIS PING ===")
    print(run(c, "docker exec astro-tma-redis-1 redis-cli ping"))
    print("\n=== POSTGRES ===")
    print(run(c, "docker exec astro-tma-postgres-1 pg_isready -U astro -d astro_tma"))
    print("\n=== YUKASSA ENV (names only) ===")
    print(run(c, "grep -E '^YUKASSA_|^TELEGRAM_WEBHOOK_URL=' /opt/astro-tma/.env | sed 's/=.*/=***/'"))
    print("\n=== DISK ===")
    print(run(c, "df -h / | tail -1"))
    print("\n=== MEM ===")
    print(run(c, "free -h | head -2"))
    c.close()


if __name__ == "__main__":
    main()
