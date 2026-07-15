"""Deeper production checks — Telegram, YuKassa API, migrations, errors."""
from __future__ import annotations

import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "194.99.21.53"
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
    c.connect(HOST, username="root", key_filename=KEY, timeout=30)

    print("=== TELEGRAM WEBHOOK ===")
    print(
        run(
            c,
            "set -a; . /opt/astro-tma/.env; set +a; "
            "curl -s \"https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo\" "
            "| python3 -c \"import sys,json; d=json.load(sys.stdin)['result']; "
            "print('url=', d.get('url')); print('pending=', d.get('pending_update_count')); "
            "print('last_error=', d.get('last_error_message')); print('last_error_date=', d.get('last_error_date'))\"",
        )
    )

    print("\n=== TELEGRAM BOT getMe ===")
    print(
        run(
            c,
            "set -a; . /opt/astro-tma/.env; set +a; "
            "curl -s \"https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe\" "
            "| python3 -c \"import sys,json; d=json.load(sys.stdin); print(d)\"",
        )
    )

    print("\n=== YUKASSA API ME (shop auth) ===")
    print(
        run(
            c,
            "set -a; . /opt/astro-tma/.env; set +a; "
            "curl -s -o /tmp/yk.json -w 'HTTP:%{http_code}\\n' "
            "-u \"${YUKASSA_SHOP_ID}:${YUKASSA_SECRET_KEY}\" "
            "https://api.yookassa.ru/v3/me; "
            "python3 -c \"import json; d=json.load(open('/tmp/yk.json')); "
            "print({k:d.get(k) for k in ['account_id','status','test','fiscalization'] if k in d or True}); "
            "print('keys=', list(d.keys())[:12])\"",
        )
    )

    print("\n=== ALEMBIC CURRENT ===")
    print(run(c, f"{COMPOSE} exec -T backend alembic current 2>&1 | tail -5"))

    print("\n=== RECENT ERRORS (backend 2h) ===")
    print(
        run(
            c,
            "docker logs astro-tma-backend-1 --since 2h 2>&1 | "
            "grep -E '\"level\": \"error\"|ERROR|Traceback|Critical' | tail -30 "
            "|| echo '(no errors)'",
        )
    )

    print("\n=== RECENT PAYMENT EVENTS (24h) ===")
    print(
        run(
            c,
            "docker logs astro-tma-backend-1 --since 24h 2>&1 | "
            "grep -E 'yukassa\\.|webhook\\.payment|stars\\.|access_granted' | tail -40 "
            "|| echo '(no payment events)'",
        )
    )

    print("\n=== SSL CERT ===")
    print(
        run(
            c,
            "echo | openssl s_client -servername ip-194-99-21-53-142250.vps.hosted-by-mvps.net "
            "-connect 127.0.0.1:443 2>/dev/null | openssl x509 -noout -dates -subject 2>/dev/null",
        )
    )

    print("\n=== RETURN URL EFFECTIVE ===")
    print(
        run(
            c,
            f"{COMPOSE} exec -T backend python -c \""
            "from services.payments.yukassa import effective_return_url, is_configured; "
            "print('configured=', is_configured()); "
            "print('return_url=', effective_return_url())\"",
        )
    )

    print("\n=== DB COUNTS ===")
    print(
        run(
            c,
            "docker exec astro-tma-postgres-1 psql -U astro -d astro_tma -c "
            "\"SELECT (SELECT count(*) FROM users) AS users, "
            "(SELECT count(*) FROM purchases WHERE status='completed') AS purchases_ok, "
            "(SELECT count(*) FROM subscriptions WHERE status='active') AS subs_active;\"",
        )
    )

    c.close()


if __name__ == "__main__":
    main()
