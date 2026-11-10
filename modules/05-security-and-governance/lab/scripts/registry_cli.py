"""Manage prompt/policy bundles.

    uv run python scripts/registry_cli.py list
    uv run python scripts/registry_cli.py show 1.1.0
    uv run python scripts/registry_cli.py check 2.0.0        # run offline checks, change nothing
    uv run python scripts/registry_cli.py activate 1.1.0 --actor you
    uv run python scripts/registry_cli.py rollback --actor you

Every activation and rollback is written to the audit log.
"""

from __future__ import annotations

import argparse
import sys

from kestrel_docs_assistant.config import get_settings
from kestrel_docs_assistant.domain.audit import AuditLog
from kestrel_docs_assistant.domain.policy_checks import make_checker
from kestrel_docs_assistant.domain.registry import ActivationRefused, PolicyRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("show", "check"):
        sub.add_parser(name).add_argument("version")
    act = sub.add_parser("activate")
    act.add_argument("version")
    act.add_argument("--actor", required=True)
    sub.add_parser("rollback").add_argument("--actor", required=True)
    args = parser.parse_args()

    s = get_settings()
    registry = PolicyRegistry(s.registry_dir)
    checker = make_checker(s.handbook_dir, s.golden_path)
    audit = AuditLog(s.audit_log_path)

    if args.cmd == "list":
        state = registry.state()
        for v in registry.versions():
            b = registry.load(v)
            marker = "*" if v == state.active else " "
            print(f"{marker} {v:<8} reviewed_by={str(b.reviewed_by):<8} {b.description}")
        print(f"history: {' -> '.join(state.history)}")
    elif args.cmd == "show":
        print(registry.load(args.version).model_dump_json(indent=2))
    elif args.cmd == "check":
        report = checker(registry.load(args.version))
        print(report.summary())
        return 0 if report.passed else 1
    elif args.cmd == "activate":
        try:
            report = registry.activate(args.version, checker)
        except ActivationRefused as exc:
            audit.append("policy_activation_refused", actor=args.actor, version=args.version,
                         failed=[r.name for r in exc.report.results if not r.passed])
            print(exc)
            return 1
        audit.append("policy_activated", actor=args.actor, version=args.version)
        print(report.summary())
        print(f"✅ {args.version} is now active. Restart the service to load it.")
    elif args.cmd == "rollback":
        previous = registry.state().active
        active = registry.rollback()
        audit.append("policy_rolled_back", actor=args.actor, from_version=previous, to_version=active)
        print(f"↩️  rolled back {previous} -> {active}. Restart the service to load it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
