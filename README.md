# envlayer-audit

Explain **which configuration layer defines each key**, without printing values.
Catch forbidden overrides before a deployment. Python 3.10+, no runtime dependencies.

[简体中文](docs/zh-CN.md) · [Русский](docs/ru.md) · [Deutsch](docs/de.md)

## Why this exists

A base file, an environment file, and a developer override may each define the same
key. Reviewing them separately does not show the final assignment chain. This tool
produces an ordered provenance report and enforces an exact-key policy. It does not
load settings into your application or change files or process environment variables.

## Start in a checkout

```sh
python -m envlayer_audit examples/base.env examples/production.env --policy examples/policy.json
```

```text
envlayer-audit: PASS; 2 layers; 3 keys
LOG_LEVEL: L1:4 -> L2:1 (1 overrides)
REGION: L1:3 (0 overrides)
SERVICE_NAME: L1:2 (0 overrides)
```

Arguments are ordered **lowest to highest precedence**. `L1` is the first file.
The last valid assignment wins, including repeated assignments within one file.
All reassignments count as overrides, even when the values are identical; values
are deliberately not compared. No automatic `.env*` discovery or `NODE_ENV` logic.

```sh
python -m envlayer_audit config/base.env config/staging.env --format json
python -m unittest discover -s tests -v
```

Optional local installation: `python -m pip install .` gives the `envlayer-audit`
command. Build tooling requires setuptools 77+ and pip may download it; running
from a checkout needs neither pip nor downloads. This project is not yet published
to PyPI. The package name here is not a claim that a registry name is reserved.

## Policies

Pass a UTF-8 JSON file using `--policy`:

```json
{
  "required": ["SERVICE_NAME", "REGION"],
  "allowed": ["SERVICE_NAME", "REGION", "LOG_LEVEL"],
  "protected": ["REGION"]
}
```

- `required`: keys must be assigned at least once. Empty values count as present.
- `allowed`: if present, only these keys may occur. An empty list allows no keys.
  If omitted, any syntactically valid key is allowed.
- `protected`: a key may be assigned at most once across the entire input,
  including duplicates in the same file. It need not exist unless also required.

Lists contain exact, case-sensitive ASCII key names, without globs. Duplicate list
entries, unknown fields, non-object policies, duplicate JSON object fields, and
required keys outside `allowed` are errors. If any assignment cannot be parsed,
`complete` is false and **all policy evaluation is skipped**; the command fails.
The partial provenance is for diagnosis, not a validated effective configuration.

Exit codes: `0` complete and policy-compliant; `1` syntax or policy violations;
`2` unreadable files, invalid UTF-8, invalid policy or command arguments. I/O and
policy-load failures use a generic stderr message, even with `--format json`.
Policies exceeding the JSON parser's nesting limit also exit `2` with this generic
message, without a traceback or paths.

## Deliberately small syntax

This is an audit dialect, **not full dotenv or shell compatibility**:

- UTF-8 text, LF or CRLF, no BOM. Blank lines and lines starting with `#` after
  ASCII space/tab trimming are ignored.
- Optional `export` followed by a space/tab; key `[A-Za-z_][A-Za-z0-9_]*`;
  optional spaces/tabs around `=`. Keys are case-sensitive.
- Values are single-line, empty, unquoted, single-quoted or double-quoted.
  In double quotes a backslash escapes the next character for quote matching;
  single quotes have no escapes. After a closing quote, only whitespace or a
  whitespace-separated `#` comment is accepted.
- Unquoted values cannot contain quotes or end in a backslash. A value starting
  with `#` is accepted as a comment/empty assignment. Other unquoted comment
  interpretation is irrelevant to this value-blind report.
- ASCII control characters other than tab are rejected in assignment lines.
  No multiline values, continuations, key-only declarations or `KEY: value`.
- No expansion, escape decoding, substitution, execution, or type checking occurs.
  `$VAR`, `${VAR}`, `$(...)` and backticks are opaque value characters.

If your loader accepts other syntax or has different precedence, this report is
not its runtime configuration. Repeated file arguments are repeated layers. Missing
files are errors, never silently skipped. The library accepts zero layers; the CLI
requires at least one. Large files are read into memory; there is no streaming mode.

## JSON and library

`--format json` emits deterministic key-sorted JSON with `schema_version: 1`,
`ok`, `complete`, `layer_count`, `keys` and `diagnostics`. Each key has `winner`,
`history` and `overrides`; each location includes `key`, one-based `layer` and
one-based `line`. Diagnostic codes are `invalid_assignment`,
`unsupported_value_syntax`, `missing_required`, `not_allowed`, and
`protected_redefined`. Consumers should tolerate additional fields in future v1
reports. History preserves input order. No paths or value hashes are emitted.

```python
from envlayer_audit import audit

report = audit(["REGION=demo\nLEVEL=info", "LEVEL=warn"],
               {"required": ["REGION"], "protected": ["REGION"]})
assert report["ok"]
assert report["keys"][0]["overrides"] == 1
```

`parse_layer(text, layer)` returns `(occurrences, diagnostics)` without RHS data.
`validate_policy(policy)` returns a valid policy or raises a generic `ValueError`.
The caller owns text strings passed to the library and must avoid logging them.

## Privacy boundary

Reports include valid key names and source line numbers. Do not place secrets in
key names. Numeric layer IDs prevent filenames from leaking through reports.
Malformed source lines, RHS values, exception text, paths, value lengths and value
hashes are not emitted. This is output minimization, not secure erasure: input text
exists in process memory and the tool is not hardened against hostile Python
embedding, memory inspection, shell history, crash dumps or OS-level monitoring.
Argparse errors intentionally omit offending argument text.

## Relationship to existing tools

Reviewed upstream documentation on 2026-10-03:

- [dotenv-linter](https://github.com/dotenv-linter/dotenv-linter) provides lint,
  fix and comparison workflows, including duplicate keys and schema violations.
- [dotenv-flow](https://github.com/kerimdzhanov/dotenv-flow) loads environment-specific
  files and local overrides into Node.js process configuration.

This project's focus is explicit arbitrary layer order, line-level assignment
history, and a no-redefinition rule with value-blind output. It complements those
tools; it does not claim to replace their parsers, cover every feature they have,
or reproduce dotenv-flow's resolution rules. Implementation is original Python
standard-library code; no upstream source was copied.

## Development and scope

Run `python -m unittest discover -s tests -v`. GitHub Actions runs the same tests
on Python 3.10–3.14. Local validation was on Python 3.12; remote CI results must be
checked separately. Tests cover grammar boundaries, duplicate assignments, policy
validation, environment non-mutation, CLI exit codes and redaction regressions.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
Licensed under [MIT](LICENSE).
