import paramiko, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = '194.99.21.53'
USER = 'root'
PASS = 'HbqSgXEkc834Wy'
COMPOSE = 'docker compose -f /opt/astro-tma/docker-compose.yml'

def ssh_run(client, cmd, timeout=120):
    print(f'  → {cmd}')
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    if out: print(out)
    return out

def main():
    t0 = time.time()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)

    ssh_run(client, 'cd /opt/astro-tma && git pull origin main 2>&1 | tail -5')
    ssh_run(client, f'{COMPOSE} exec -T backend alembic upgrade head 2>&1 | tail -5')
    ssh_run(client, 'cp /opt/astro-tma/infra/scripts/seed_natal_interpretations.py /opt/astro-tma/backend/scripts/')
    ssh_run(client, 'cp /opt/astro-tma/infra/scripts/natal_interpretations.md /opt/astro-tma/backend/scripts/')
    ssh_run(client, f'{COMPOSE} exec -T -e PYTHONPATH=/app backend python /app/scripts/seed_natal_interpretations.py 2>&1 | tail -5')
    ssh_run(client, f'{COMPOSE} restart backend 2>&1 | tail -3')
    time.sleep(4)
    logs = ssh_run(client, 'docker logs astro-tma-backend-1 --tail 3 2>&1')
    print('  ✓ OK' if 'startup complete' in logs else '  ✗ Check logs')
    client.close()
    print(f'\n══ Done in {time.time()-t0:.0f}s ══')

if __name__ == '__main__':
    main()
