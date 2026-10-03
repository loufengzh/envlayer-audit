import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from envlayer_audit import audit, parse_layer, validate_policy
from envlayer_audit.__main__ import main, render


class AuditTests(unittest.TestCase):
    def test_order_and_provenance(self):
        result = audit(['B=1\nA=2\nA=3', 'A=4'])
        self.assertTrue(result['ok'])
        a, b = result['keys']
        self.assertEqual(a['key'], 'A')
        self.assertEqual(a['winner'], {'key': 'A', 'layer': 2, 'line': 1})
        self.assertEqual(a['overrides'], 2)
        self.assertEqual(b['winner']['layer'], 1)

    def test_supported_syntax(self):
        text = "# hi\r\nexport X = 'a # b' # comment\r\nEMPTY=\nY=unquoted # hi\nZ=\"escaped \\\" quote\"\n"
        result = audit([text])
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['keys']), 4)

    def test_no_evaluation(self):
        result = audit(['X=$(false)\nY=${MISSING}\nZ=`false`'])
        self.assertTrue(result['ok'])

    def test_unsupported_syntax(self):
        for text in ['X="unterminated', "X='a'b", 'X=a\\', 'NO_EQUALS', 'BAD-KEY=a', 'X=abc\x00def', 'X=abc\r', 'X=abc\x7fdef', '\ufeffX=a', 'X="a"#comment']:
            with self.subTest(text=text):
                result = audit([text], {'required': ['MISSING']})
                self.assertFalse(result['complete'])
                self.assertEqual(len(result['diagnostics']), 1)
                self.assertNotEqual(result['diagnostics'][0]['code'], 'missing_required')

    def test_policies(self):
        result = audit(['A=\nB=one', 'B=one\nC=two'], {
            'required': ['A', 'D'], 'allowed': ['A', 'B', 'D'], 'protected': ['B']})
        self.assertTrue(result['complete'])
        self.assertEqual([x['code'] for x in result['diagnostics']],
                         ['missing_required', 'protected_redefined', 'not_allowed'])

    def test_protected_duplicate_same_layer(self):
        self.assertEqual(audit(['A=1\nA=1'], {'protected': ['A']})['diagnostics'][0]['code'], 'protected_redefined')

    def test_allowed_empty_and_absent(self):
        self.assertTrue(audit(['A=1'])['ok'])
        self.assertFalse(audit(['A=1'], {'allowed': []})['ok'])

    def test_invalid_policies(self):
        for policy in [[], None, {'allowd': []}, {'required': 'A'}, {'allowed': [1]},
                       {'required': ['A', 'A']}, {'protected': ['BAD-KEY']},
                       {'required': ['A'], 'allowed': []}]:
            with self.subTest(policy=policy):
                with self.assertRaises(ValueError):
                    validate_policy(policy)

    def test_empty(self):
        self.assertEqual(audit([])['layer_count'], 0)
        self.assertTrue(audit(['', '# comment'])['ok'])

    def test_value_redaction(self):
        sentinel = 'UNIQUE_PRIVATE_VALUE_9876'
        for text in [f'A={sentinel}', f'A="{sentinel}', f'{sentinel}-bad', f'A={sentinel}\x00']:
            result = audit([text])
            self.assertNotIn(sentinel, json.dumps(result))
            self.assertNotIn(sentinel, render(result))
            self.assertNotIn(sentinel, repr(parse_layer(text, 1)))

    def test_process_environment_untouched(self):
        before = dict(os.environ)
        audit(['PATH=fictional'])
        self.assertEqual(dict(os.environ), before)


class CLITests(unittest.TestCase):
    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_success_and_policy_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            layer = Path(directory) / 'layer.env'
            policy = Path(directory) / 'policy.json'
            layer.write_text('A=PRIVATE_VALUE', encoding='utf-8')
            policy.write_text('{"required":["B"]}', encoding='utf-8')
            code, out, err = self.invoke([str(layer), '--format', 'json'])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(out)['ok'])
            self.assertNotIn('PRIVATE_VALUE', out + err)
            self.assertEqual(self.invoke([str(layer), '--policy', str(policy)])[0], 1)

    def test_io_error_path_redacted(self):
        code, out, err = self.invoke(['/missing/PRIVATE_PATH_987.env'])
        self.assertEqual(code, 2)
        self.assertNotIn('PRIVATE_PATH_987', out + err)
        self.assertNotIn('Traceback', err)

    def test_policy_errors_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            layer = Path(directory) / 'a.env'
            policy = Path(directory) / 'policy.json'
            layer.write_text('A=secret', encoding='utf-8')
            for value in ['{"PRIVATE_VALUE":[]}', '{"required": ["PRIVATE_VALUE",}',
                          '{"required":[],"required":[]}', 'null']:
                policy.write_text(value, encoding='utf-8')
                code, out, err = self.invoke([str(layer), '--policy', str(policy)])
                self.assertEqual(code, 2)
                self.assertNotIn('PRIVATE_VALUE', out + err)

    def test_bare_cr_rejected_without_newline_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            layer = Path(directory) / 'a.env'
            layer.write_bytes(b'A=PRIVATE_VALUE\rB=two')
            code, out, err = self.invoke([str(layer), '--format', 'json'])
            self.assertEqual(code, 1)
            report = json.loads(out)
            self.assertFalse(report['complete'])
            self.assertEqual(report['diagnostics'][0]['code'], 'invalid_assignment')
            self.assertEqual(report, audit(['A=PRIVATE_VALUE\rB=two']))
            self.assertNotIn('PRIVATE_VALUE', out + err)

    def test_crlf_preserved_and_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            layer = Path(directory) / 'a.env'
            layer.write_bytes(b'A=one\r\nB=two\r\n')
            code, out, err = self.invoke([str(layer), '--format', 'json'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out), audit(['A=one\r\nB=two\r\n']))

    def test_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            layer = Path(directory) / 'a.env'
            layer.write_bytes(b'A=\xff')
            self.assertEqual(self.invoke([str(layer)])[0], 2)

    def test_argument_error_redacted(self):
        proc = subprocess.run([sys.executable, '-m', 'envlayer_audit', '--PRIVATE_ARGUMENT'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn('PRIVATE_ARGUMENT', proc.stdout + proc.stderr)

    def test_module_entrypoint(self):
        proc = subprocess.run([sys.executable, '-m', 'envlayer_audit', 'examples/base.env', 'examples/production.env', '--policy', 'examples/policy.json'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('LOG_LEVEL: L1:4 -> L2:1', proc.stdout)


if __name__ == '__main__':
    unittest.main()
