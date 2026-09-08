import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'packaging/install.sh'

class BootstrapTests(unittest.TestCase):
    def test_private_bootstrap_verifies_before_execution_and_passes_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b'#!/bin/sh\nprintf "%s\\n" "$@" > "$TEST_RESULT"\n'
            setup = root/'setup';setup.write_bytes(payload)
            result = root/'result'
            fixtures = root/'bin';fixtures.mkdir()
            scripts = {
                'uname': '#!/bin/sh\nif test "$1" = -s; then echo Linux; else echo x86_64; fi\n',
                'id': '#!/bin/sh\necho 1000\n',
                'gh': '''#!/bin/sh
case "$1" in
 auth) exit 0 ;;
 api) echo "$TEST_DIGEST" ;;
 release)
  while test "$#" -gt 0; do
   case "$1" in --dir) dir=$2; shift 2;; *) shift;; esac
  done
  cp "$TEST_SETUP" "$dir/notryn-setup-linux-x86_64" ;;
esac
'''
            }
            for name, script in scripts.items():
                file=fixtures/name;file.write_text(script);file.chmod(0o755)
            env={**os.environ,'PATH':str(fixtures)+os.pathsep+os.environ['PATH'],'TEST_SETUP':str(setup),'TEST_RESULT':str(result),'TEST_DIGEST':'sha256:'+hashlib.sha256(payload).hexdigest()}
            command=['sh',str(SCRIPT),'--private','--no-open','--version','0.2.0-alpha.3']
            good=subprocess.run(command,env=env,capture_output=True,text=True,errors='replace')
            self.assertEqual(good.returncode,0,good.stderr)
            self.assertTrue(result.exists(), good.stdout + '\n' + good.stderr)
            self.assertEqual(result.read_text().splitlines(),['--version','0.2.0-alpha.3','--private','--no-open'])
            result.unlink()
            env['TEST_DIGEST']='sha256:'+'0'*64
            bad=subprocess.run(command,env=env,capture_output=True,text=True,errors='replace')
            self.assertNotEqual(bad.returncode,0)
            self.assertIn('checksum mismatch',bad.stderr)
            self.assertFalse(result.exists())
            malformed=subprocess.run(['sh',str(SCRIPT),'--version','../../oops'],env=env,capture_output=True,text=True,errors='replace')
            self.assertNotEqual(malformed.returncode,0)
            self.assertFalse(result.exists())

if __name__=='__main__':unittest.main()
