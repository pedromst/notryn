import hashlib
import os
import pty
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

    def test_public_bootstrap_progress_with_piped_input_and_tty_or_log_output(self):
        for terminal in [False, True]:
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixtures = root / 'bin'; fixtures.mkdir()
                payload = b'#!/bin/sh\necho complete > "$TEST_RESULT"\n'
                setup = root / 'setup'; setup.write_bytes(payload)
                scripts = {
                    'uname': '#!/bin/sh\nif test "$1" = -s; then echo Linux; else echo x86_64; fi\n',
                    'id': '#!/bin/sh\necho 1000\n',
                    'curl': '''#!/bin/sh
printf "%s " "$@" >> "$TEST_CURL_ARGS"
printf "\\n" >> "$TEST_CURL_ARGS"
checksum=0
while test "$#" -gt 0; do
 case "$1" in
  -o) target=$2; shift 2 ;;
  *.sha256) checksum=1; shift ;;
  *) shift ;;
 esac
done
if test "$checksum" -eq 1; then printf "%s  setup\\n" "$TEST_DIGEST" > "$target"; else cp "$TEST_SETUP" "$target"; fi
'''
                }
                for name, script in scripts.items():
                    path=fixtures/name; path.write_text(script); path.chmod(0o755)
                result = root / 'result'; curl_args = root / 'curl-args'
                env={**os.environ, 'PATH':str(fixtures)+os.pathsep+os.environ['PATH'], 'TERM':'xterm-256color',
                     'TEST_SETUP':str(setup), 'TEST_RESULT':str(result), 'TEST_CURL_ARGS':str(curl_args),
                     'TEST_DIGEST':hashlib.sha256(payload).hexdigest()}
                master, slave = pty.openpty()
                try:
                    completed=subprocess.run(['sh',str(SCRIPT),'--no-open'],input=b'',stdout=subprocess.PIPE,
                                             stderr=slave if terminal else subprocess.PIPE,env=env)
                finally:
                    os.close(slave); os.close(master)
                self.assertEqual(completed.returncode,0,completed.stderr)
                self.assertEqual(result.read_text().strip(),'complete')
                first=curl_args.read_text().splitlines()[0]
                self.assertIn('--progress-bar' if terminal else '--silent',first)
                if not terminal:
                    self.assertIn(b'Downloading installer...',completed.stderr)
                    self.assertIn(b'Installer verified. Starting setup...',completed.stderr)
                    self.assertNotIn(b'\x1b',completed.stderr)
                result.unlink(); env['TEST_DIGEST']='0'*64
                failed=subprocess.run(['sh',str(SCRIPT),'--no-open'],input=b'',capture_output=True,env=env)
                self.assertNotEqual(failed.returncode,0)
                self.assertFalse(result.exists())
                self.assertNotIn(b'Installer verified.',failed.stderr)

if __name__=='__main__':unittest.main()
