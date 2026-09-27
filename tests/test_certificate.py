"""Exercise certificate validation/publication with real local OpenSSL certificates."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1]/'docker/certbot/certificate.py'

class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.live = self.root/'le/live/cars.example.com'
        self.live.mkdir(parents=True)
        self.env = {**os.environ, 'DOMAIN':'cars.example.com', 'STAGING':'0',
                    'LE_DIR':str(self.root/'le'), 'PUBLIC_DIR':str(self.root/'public'),
                    'SSL_CERT_FILE':str(self.root/'ca.pem')}
        self.openssl('req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256',
                     '-nodes','-keyout','ca.key','-out','ca.pem','-days','60','-subj','/CN=Test CA',
                     '-addext','basicConstraints=critical,CA:TRUE')
        self.openssl('req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256',
                     '-nodes','-keyout',str(self.live/'privkey.pem'),'-out','leaf.csr',
                     '-subj','/CN=cars.example.com')
        (self.root/'ext').write_text('subjectAltName=DNS:cars.example.com\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n')
        self.openssl('x509','-req','-in','leaf.csr','-CA','ca.pem','-CAkey','ca.key',
                     '-CAcreateserial','-out',str(self.live/'cert.pem'),'-days','45','-extfile','ext')
        (self.live/'chain.pem').write_bytes((self.root/'ca.pem').read_bytes())
        (self.live/'fullchain.pem').write_bytes((self.live/'cert.pem').read_bytes()+(self.root/'ca.pem').read_bytes())

    def openssl(self, *args):
        subprocess.run(['openssl', *args], cwd=self.root, check=True, capture_output=True)

    def helper(self, command, **env):
        return subprocess.run([sys.executable,str(HELPER),command],env={**self.env,**env},capture_output=True,text=True)

    def test_valid_pair_published_atomically(self):
        r=self.helper('publish')
        self.assertEqual(r.returncode,0,r.stderr)
        current=self.root/'public/current'
        self.assertTrue(current.is_symlink())
        self.assertEqual((current/'privkey.pem').stat().st_mode & 0o777,0o600)
        self.assertEqual(self.helper('ready').returncode,0)

    def test_untrusted_chain_preserves_previous_pair(self):
        self.assertEqual(self.helper('publish').returncode,0)
        previous=os.readlink(self.root/'public/current')
        self.env['SSL_CERT_FILE']=str(self.root/'missing-ca.pem')
        self.assertNotEqual(self.helper('publish').returncode,0)
        self.assertEqual(os.readlink(self.root/'public/current'),previous)

    def test_mismatched_key_rejected(self):
        (self.live/'privkey.pem').write_bytes((self.root/'ca.key').read_bytes())
        self.assertNotEqual(self.helper('publish').returncode,0)
        self.assertFalse((self.root/'public/current').exists())

    def test_placeholder_backed_up_never_published(self):
        self.openssl('req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256',
                     '-nodes','-keyout',str(self.live/'privkey.pem'),'-out',str(self.live/'fullchain.pem'),
                     '-days','3','-subj','/CN=cars.example.com')
        self.assertEqual(self.helper('state').stdout.strip(),'selfsigned')
        self.assertNotEqual(self.helper('publish').returncode,0)
        self.assertEqual(self.helper('prepare').returncode,0)
        self.assertFalse(self.live.exists())
        self.assertEqual(len(list((self.root/'le/legacy-backups').glob('*/live/fullchain.pem'))),1)

if __name__ == '__main__': unittest.main()
