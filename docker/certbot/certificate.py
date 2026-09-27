"""Validate ACME state and atomically publish a separate nginx certificate pair."""
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time

DOMAIN = os.environ['DOMAIN']
if not re.fullmatch(r'[A-Za-z0-9.-]+', DOMAIN) or '/' in DOMAIN or '..' in DOMAIN:
    raise SystemExit('Invalid DOMAIN')
LE = Path(os.environ.get('LE_DIR', '/etc/letsencrypt'))
PUBLIC = Path(os.environ.get('PUBLIC_DIR', '/etc/nginx/public'))
LIVE = LE / 'live' / DOMAIN
STAGING = os.environ.get('STAGING', '0') == '1'

def openssl(*args):
    return subprocess.check_output(['openssl', *map(str, args)], stderr=subprocess.PIPE, text=True).strip()

def state():
    cert = LIVE / 'fullchain.pem'
    if not cert.exists():
        return 'missing'
    issuer = openssl('x509', '-in', cert, '-noout', '-issuer').split('=', 1)[1].strip()
    subject = openssl('x509', '-in', cert, '-noout', '-subject').split('=', 1)[1].strip()
    if issuer == subject:
        return 'selfsigned'
    return 'staging' if any(x in issuer.lower() for x in ('staging', 'fake', 'pretend')) else 'production'

def validate():
    kind = state()
    expected = 'staging' if STAGING else 'production'
    if kind != expected:
        raise ValueError(f'Expected {expected} certificate, found {kind}')
    cert, key = LIVE/'fullchain.pem', LIVE/'privkey.pem'
    openssl('x509', '-in', cert, '-noout', '-checkend', '0')
    openssl('x509', '-in', cert, '-noout', '-checkhost', DOMAIN)
    # Checks PEM readability and that the private key matches the certificate.
    ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cert, key)
    if not STAGING:
        openssl('verify', '-purpose', 'sslserver', '-verify_hostname', DOMAIN,
                '-untrusted', LIVE/'chain.pem', cert)

def prepare():
    if state() != 'selfsigned':
        return
    if (LE/'renewal'/f'{DOMAIN}.conf').exists() or (LIVE/'fullchain.pem').is_symlink():
        raise ValueError('Self-signed managed lineage: inspect it and use make prod-cert-reset explicitly')
    backup = LE/'legacy-backups'/f'{DOMAIN}-{time.time_ns()}'
    backup.mkdir(parents=True, mode=0o700)
    shutil.move(str(LIVE), str(backup/'live'))
    print(f'Legacy placeholder preserved in {backup}')

def publish():
    validate()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    bundle = Path(tempfile.mkdtemp(prefix='bundle-', dir=PUBLIC))
    for name in ('fullchain.pem', 'privkey.pem'):
        shutil.copyfile(LIVE/name, bundle/name)
        (bundle/name).chmod(0o600 if name == 'privkey.pem' else 0o644)
    # One symlink switch publishes both files together; old pair remains on failure.
    link = PUBLIC/f'.current-{os.getpid()}'
    link.symlink_to(bundle.name, target_is_directory=True)
    os.replace(link, PUBLIC/'current')
    print('Validated certificate published for nginx')

if __name__ == '__main__':
    try:
        command = sys.argv[1]
        if command == 'state': print(state())
        elif command == 'prepare': prepare()
        elif command == 'publish': publish()
        elif command == 'validate': validate()
        elif command == 'ready':
            validate()
            openssl('x509', '-in', LIVE/'fullchain.pem', '-noout', '-checkend', '2592000')
        else: raise ValueError('Expected state, prepare, validate or publish')
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Certificate error: {exc}', file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
