"""CLI: paths are deliberately not included in reports or errors."""
import argparse
import json
import sys
from pathlib import Path
from .core import audit, validate_policy


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, "envlayer-audit: invalid command arguments; use --help\n")


def read_text(path):
    with Path(path).open(encoding="utf-8", newline="") as source:
        return source.read()


def render(report):
    lines = [f"envlayer-audit: {'PASS' if report['ok'] else 'FAIL'}; "
             f"{report['layer_count']} layers; {len(report['keys'])} keys"]
    if not report["complete"]:
        lines.append("Incomplete parse; policy evaluation skipped.")
    for entry in report["keys"]:
        chain = " -> ".join(f"L{o['layer']}:{o['line']}" for o in entry["history"])
        lines.append(f"{entry['key']}: {chain} ({entry['overrides']} overrides)")
    for issue in report["diagnostics"]:
        location = f" L{issue['layer']}:{issue['line']}" if "layer" in issue else ""
        lines.append(f"ERROR {issue['code']}{location}" + (f" {issue['key']}" if "key" in issue else ""))
    return "\n".join(lines)


def main(argv=None):
    parser = SafeParser(description="Audit explicit .env layers in low-to-high precedence, without printing values.")
    parser.add_argument("layers", nargs="+", help="input files; last assignment wins")
    parser.add_argument("--policy", help="JSON required/allowed/protected key lists")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        policy = json.loads(read_text(args.policy), object_pairs_hook=_unique_object) if args.policy else {}
        validate_policy(policy)
        report = audit((read_text(path) for path in args.layers), policy)
    except (OSError, UnicodeError, ValueError, RecursionError):
        # Never interpolate exception text: it can contain paths or file contents.
        print("envlayer-audit: input or policy could not be read or validated", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True) if args.format == "json" else render(report))
    return 0 if report["ok"] else 1


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_policy")
        result[key] = value
    return result


if __name__ == "__main__":
    sys.exit(main())
