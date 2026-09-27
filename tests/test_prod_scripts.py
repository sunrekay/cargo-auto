"""Deployment contract tests: fake Docker/Make/curl, no network or containers."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin = Path(self.tmp.name)
        self.log = self.bin / 'calls'
        self.env = dict(os.environ, DOMAIN='cars.example.com', ACME_EMAIL='ops@example.com',
                        STAGING='0', DATABASE_URL='sqlite:///data/cargo-auto.db',
                        PATH=str(self.bin)+':'+os.environ['PATH'], LOG=str(self.log))
        self.tool('docker', 'echo "docker $*" >> "$LOG"\ncase "$*" in *"certificate.py state"*) echo missing;; esac\n')
        self.tool('make', 'echo "make $*" >> "$LOG"\ncase "$*" in *"${FAIL_TARGET:-NEVER}"*) exit 7;; esac\n')
        self.tool('curl', 'echo "curl $*" >> "$LOG"\nexit "${CURL_STATUS:-0}"\n')
        self.tool('sleep', ':\n')
        self.env['DOCKER'] = str(self.bin/'docker')
        self.env['MAKE'] = str(self.bin/'make')

    def tool(self, name, body):
        p = self.bin/name
        p.write_text('#!/bin/bash\n'+body)
        p.chmod(0o755)

    def run_script(self, name, **env):
        return subprocess.run(['bash', str(ROOT/'scripts'/name)], env={**self.env, **env},
                              capture_output=True, text=True)

    def calls(self):
        return self.log.read_text() if self.log.exists() else ''

    def test_order(self):
        r = self.run_script('prod-start.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        steps = ['prod-init', 'build api nginx certbot', 'prod-cert-issue', '--wait --wait-timeout',
                 'up -d certbot', 'prod-verify']
        offsets = [calls.index(x) for x in steps]
        self.assertEqual(offsets, sorted(offsets))

    def test_certificate_failure_stops_deployment(self):
        r = self.run_script('prod-start.sh', FAIL_TARGET='prod-cert-issue')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('prod-verify', self.calls())
        self.assertNotIn('6/6 Ready', r.stdout)

    def test_preflight_failure_does_not_build(self):
        r = self.run_script('prod-start.sh', FAIL_TARGET='prod-init')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('docker', self.calls())

    def test_public_verification_enforces_tls(self):
        self.assertEqual(self.run_script('prod-verify.sh').returncode, 0)
        calls = self.calls()
        for route in ['/api/health', '/', '/api/cars']:
            self.assertIn('https://cars.example.com'+route, calls)
        self.assertNotIn(' --insecure', calls)
        self.assertNotIn(' -k', calls)

    def test_public_failure_is_fatal(self):
        self.assertNotEqual(self.run_script('prod-verify.sh', CURL_STATUS='22').returncode, 0)

    def test_invalid_domain_fails_before_docker(self):
        self.assertNotEqual(self.run_script('prod-check.sh', DOMAIN='https://bad/path').returncode, 0)
        self.assertEqual(self.calls(), '')

    def test_missing_catalogue_fails_before_docker(self):
        self.assertNotEqual(self.run_script('prod-check.sh', DATABASE_URL='sqlite:///data/missing.db').returncode, 0)
        self.assertEqual(self.calls(), '')

    def test_certbot_failure_restores_running_services(self):
        self.tool('docker', '''echo "docker $*" >> "$LOG"
case "$*" in
 *"certificate.py state"*) echo missing;;
 *"ps --status running"*) echo running-id;;
 *certonly*) exit 9;;
esac
''')
        r = self.run_script('prod-cert.sh')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('start nginx', self.calls())
        self.assertIn('start certbot', self.calls())
        self.assertNotIn('certificate.py publish', self.calls())

    def test_staging_cannot_replace_production_cert(self):
        self.tool('docker', 'echo "docker $*" >> "$LOG"\ncase "$*" in *"certificate.py state"*) echo production;; esac\n')
        self.assertNotEqual(self.run_script('prod-cert.sh', STAGING='1').returncode, 0)
        self.assertNotIn('certonly', self.calls())
        self.assertNotIn('stop certbot', self.calls())

    def test_tls_error_is_visible_and_not_retried(self):
        self.tool('curl', 'echo "curl $*" >> "$LOG"\necho "SSL certificate problem: self signed certificate" >&2\nexit 60\n')
        r = self.run_script('prod-verify.sh')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('self signed certificate', r.stderr)
        self.assertEqual(self.calls().count('curl '), 1)

    def test_first_issue_stops_proxy_then_publishes(self):
        r = self.run_script('prod-cert.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.calls()
        steps = ['stop certbot nginx', 'certificate.py prepare', '-p 80:80', '--standalone', 'certificate.py publish']
        positions = [calls.index(x) for x in steps]
        self.assertEqual(positions, sorted(positions))

    def test_valid_certificate_reused_without_downtime(self):
        self.tool('docker', 'echo "docker $*" >> "$LOG"\ncase "$*" in *"certificate.py state"*) echo production;; esac\n')
        r = self.run_script('prod-cert.sh')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('certificate.py ready', self.calls())
        self.assertIn('certificate.py publish', self.calls())
        self.assertNotIn('stop certbot', self.calls())
        self.assertNotIn('certonly', self.calls())

    def test_publish_failure_does_not_start_new_proxy(self):
        self.tool('docker', '''echo "docker $*" >> "$LOG"
case "$*" in *"certificate.py state"*) echo missing;; *"certificate.py publish"*) exit 8;; esac
''')
        self.assertNotEqual(self.run_script('prod-cert.sh').returncode, 0)
        self.assertNotIn('up -d --no-deps nginx', self.calls())

if __name__ == '__main__':
    unittest.main()
