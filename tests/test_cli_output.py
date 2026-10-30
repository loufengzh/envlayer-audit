"""Real subprocess coverage for output failures, including buffered writes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class OutputErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.layer = self.root / 'private-layer.env'
        self.layer.write_text('KEY=private-value\n', encoding='utf-8')
        self.policy = self.root / 'private-policy.json'
        self.policy.write_text(json.dumps({'required': ['MISSING']}), encoding='utf-8')

    def commands(self):
        for fmt in ('text', 'json'):
            for gate in ([], ['--policy', str(self.policy)]):
                yield [str(self.layer), '--format', fmt] + gate

    def assert_failure(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, b'envlayer-audit: output could not be written\n')

    @unittest.skipUnless(Path('/dev/full').exists(), 'requires /dev/full')
    def test_full_device_small_and_large(self):
        for size in (1, 600):
            self.layer.write_text(''.join(f'KEY{i}=private-value\n' for i in range(size)), encoding='utf-8')
            for args in self.commands():
                with self.subTest(size=size, args=args), open('/dev/full', 'wb') as output:
                    result = subprocess.run([sys.executable, '-m', 'envlayer_audit'] + args,
                                            stdout=output, stderr=subprocess.PIPE)
                self.assert_failure(result)

    def test_closed_pipe_small_and_large(self):
        for size in (1, 600):
            self.layer.write_text(''.join(f'KEY{i}=private-value\n' for i in range(size)), encoding='utf-8')
            for args in self.commands():
                with self.subTest(size=size, args=args):
                    reader, writer = os.pipe()
                    os.close(reader)
                    with os.fdopen(writer, 'wb') as output:
                        result = subprocess.run([sys.executable, '-m', 'envlayer_audit'] + args,
                                                stdout=output, stderr=subprocess.PIPE)
                    self.assert_failure(result)

    @unittest.skipUnless(os.name == 'posix', 'requires POSIX descriptor inheritance')
    def test_stdout_absent_at_startup(self):
        launcher = ('import os, sys; os.close(1); '
                    'os.execv(sys.executable, [sys.executable, "-m", "envlayer_audit"] + sys.argv[1:])')
        for args in self.commands():
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, '-c', launcher] + args, capture_output=True)
                self.assert_failure(result)
                self.assertEqual(result.stdout, b'')

    def test_closed_stream_or_descriptor(self):
        for close in ('sys.stdout.close()', 'os.close(sys.stdout.fileno())'):
            for args in self.commands():
                with self.subTest(close=close, args=args):
                    launcher = ('import os, sys; from envlayer_audit.__main__ import main; '
                                + close + '; sys.exit(main(sys.argv[1:]))')
                    result = subprocess.run([sys.executable, '-c', launcher] + args, capture_output=True)
                    self.assert_failure(result)
                    self.assertEqual(result.stdout, b'')

    def test_descriptor_free_stream_does_not_leak_exception(self):
        launcher = ('import sys; from envlayer_audit.__main__ import main; '
                    'exec("class Sink:\\n def write(self, value): raise OSError(\\\"private-detail\\\")\\n def flush(self): raise OSError(\\\"private-detail\\\")"); '
                    'sys.stdout = Sink(); sys.exit(main(sys.argv[1:]))')
        result = subprocess.run([sys.executable, '-c', launcher, str(self.layer)], capture_output=True)
        self.assert_failure(result)
        self.assertEqual(result.stdout, b'')


if __name__ == '__main__':
    unittest.main()
