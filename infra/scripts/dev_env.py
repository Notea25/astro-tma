#!/usr/bin/env python3
"""Create and update an ignored local .env.dev without printing secrets."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
import tempfile
from pathlib import Path


TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


def _upsert(lines: list[str], values: dict[str, str]) -> list[str]:
    remaining = dict(values)
    result: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        key = stripped.partition("=")[0].strip() if "=" in stripped else ""
        if key in remaining and not stripped.startswith("#"):
            result.append(f"{key}={remaining.pop(key)}\n")
        else:
            result.append(line if line.endswith("\n") else f"{line}\n")

    if remaining:
        if result and result[-1].strip():
            result.append("\n")
        result.append("# Telegram development stand\n")
        result.extend(f"{key}={value}\n" for key, value in remaining.items())
    return result


def _write_env(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp:
        tmp.writelines(lines)
        tmp_path = Path(tmp.name)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def _prompt_token() -> str:
    script = (
        'text returned of (display dialog "Введите токен @astrotestdev_bot" '
        'default answer "" with hidden answer buttons {"OK"} default button "OK")'
    )
    completed = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    token = completed.stdout.strip()
    if not TOKEN_RE.fullmatch(token):
        raise SystemExit("Bot token has an invalid format")
    return token


def init_env(base_path: Path, output_path: Path, bot_username: str) -> None:
    if not base_path.is_file():
        raise SystemExit(f"Base env file not found: {base_path}")
    token = _prompt_token()
    values = {
        "APP_ENV": "development",
        "APP_DEBUG": "true",
        "AUTH_BYPASS": "false",
        "TELEGRAM_BOT_TOKEN": token,
        "TELEGRAM_BOT_USERNAME": bot_username,
        "TELEGRAM_WEBHOOK_SECRET": secrets.token_urlsafe(32),
        "TELEGRAM_WEBHOOK_URL": "https://example.invalid/api/payments/webhook",
        "TELEGRAM_WEBAPP_URL": "https://example.invalid/",
        "MINIAPP_URL": f"https://t.me/{bot_username}?startapp",
    }
    _write_env(output_path, _upsert(base_path.read_text().splitlines(True), values))
    print(f"Created {output_path} for @{bot_username}")


def set_urls(output_path: Path, backend_url: str, frontend_url: str) -> None:
    if not output_path.is_file():
        raise SystemExit(f"Dev env file not found: {output_path}")
    backend = backend_url.rstrip("/")
    frontend = frontend_url.rstrip("/") + "/"
    values = {
        "TELEGRAM_WEBHOOK_URL": f"{backend}/api/payments/webhook",
        "TELEGRAM_WEBAPP_URL": frontend,
    }
    _write_env(output_path, _upsert(output_path.read_text().splitlines(True), values))
    print(f"Updated public URLs in {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=Path(".env.dev"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--base", type=Path, default=Path(".env"))
    init_parser.add_argument("--bot-username", default="astrotestdev_bot")

    urls_parser = subparsers.add_parser("set-urls")
    urls_parser.add_argument("--backend-url", required=True)
    urls_parser.add_argument("--frontend-url", required=True)

    args = parser.parse_args()
    if args.command == "init":
        init_env(args.base, args.env, args.bot_username)
    else:
        set_urls(args.env, args.backend_url, args.frontend_url)


if __name__ == "__main__":
    main()
