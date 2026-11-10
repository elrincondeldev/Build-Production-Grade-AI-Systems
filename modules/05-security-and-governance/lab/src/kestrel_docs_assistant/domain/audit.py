"""Tamper-evident, append-only audit log (JSON Lines + SHA-256 hash chain).

📖 See lesson 5.5. Each record stores the hash of the previous record, so editing,
deleting or reordering any line breaks every hash after it. Like a blockchain
without the hype: just ``hash_n = sha256(hash_{n-1} || record_n)``.

What a hash chain does NOT protect against: someone who rewrites the *whole*
file and recomputes all hashes, or who truncates the tail. Mitigations: ship
records to write-once storage (object lock / WORM), and periodically publish
("anchor") the latest hash somewhere the attacker can't reach.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .pii import redact_structure

GENESIS_HASH = "0" * 64


def _canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def compute_hash(record_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(record_without_hash)).hexdigest()


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._load_tail()

    def _load_tail(self) -> tuple[int, str]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0, GENESIS_HASH
        last_line = self.path.read_text(encoding="utf-8").strip().splitlines()[-1]
        last = json.loads(last_line)
        return int(last["seq"]), str(last["hash"])

    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        """Append one event. PII is redacted before anything touches disk."""
        with self._lock:
            record: dict[str, Any] = {
                "seq": self._seq + 1,
                "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "event": event,
                **redact_structure(fields),  # type: ignore[dict-item]
                "prev_hash": self._last_hash,
            }
            record["hash"] = compute_hash(record)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
            self._seq, self._last_hash = record["seq"], record["hash"]
            return record


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    records: int
    first_bad_seq: int | None = None
    error: str | None = None


def verify_chain(path: Path) -> VerifyResult:
    if not path.exists():
        return VerifyResult(True, 0)
    prev_hash, expected_seq, count = GENESIS_HASH, 1, 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return VerifyResult(False, count, expected_seq, f"line {line_no}: not valid JSON")
        stored_hash = record.pop("hash", None)
        if record.get("seq") != expected_seq:
            return VerifyResult(False, count, expected_seq, f"line {line_no}: expected seq {expected_seq}, got {record.get('seq')}")
        if record.get("prev_hash") != prev_hash:
            return VerifyResult(False, count, expected_seq, f"seq {expected_seq}: prev_hash does not match previous record")
        if compute_hash(record) != stored_hash:
            return VerifyResult(False, count, expected_seq, f"seq {expected_seq}: content was modified (hash mismatch)")
        prev_hash, expected_seq, count = stored_hash, expected_seq + 1, count + 1
    return VerifyResult(True, count)
