"""Deploy latest main to VPS via SSH key."""
from __future__ import annotations

import sys
import time

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "194.99.21.53"
USER = "root"
KEY = __import__("os").path.expanduser("~/.ssh/astro_tma_deploy")
COMPOSE = "docker compose -f /opt/astro-tma/docker-compose.yml"


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 300) -> str:
    print(f">> {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print("ERR:", err.rstrip())
    return out


def main() -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=KEY, timeout=30)
    print("=== connected ===")
    run(client, "cd /opt/astro-tma && git pull origin main")
    # Never let local-dev override (reload, APP_DEBUG, published DB ports) hit prod.
    run(
        client,
        "cd /opt/astro-tma && "
        "if [ -f docker-compose.override.yml ]; then "
        "mv -f docker-compose.override.yml "
        "docker-compose.override.yml.disabled_$(date -u +%Y%m%d_%H%M%S); fi",
    )
    run(client, f"{COMPOSE} up -d --build backend worker")
    time.sleep(5)
    run(client, "curl -sk https://127.0.0.1/health")
    run(
        client,
        "curl -sk -o /dev/null -w '%{http_code}' "
        "https://127.0.0.1/api/payments/return",
    )
    client.close()


if __name__ == "__main__":
    main()
