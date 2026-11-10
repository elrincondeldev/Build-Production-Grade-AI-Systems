"""Verify the audit log hash chain.

    uv run python scripts/verify_audit_log.py                    # default path from settings
    uv run python scripts/verify_audit_log.py artifacts/audit.jsonl

Exit code 0 = intact, 1 = tampering detected (so CI or a cron job can alert).
"""

from __future__ import annotations

import sys
from pathlib import Path

from kestrel_docs_assistant.config import get_settings
from kestrel_docs_assistant.domain.audit import verify_chain


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else get_settings().audit_log_path
    result = verify_chain(path)
    if result.ok:
        print(f"OK: {result.records} records, hash chain intact ({path})")
        return 0
    print(f"TAMPERING DETECTED at seq {result.first_bad_seq}: {result.error}")
    print(f"{result.records} records verified before the break.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
