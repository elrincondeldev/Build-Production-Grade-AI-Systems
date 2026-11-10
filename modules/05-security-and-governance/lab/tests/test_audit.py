from __future__ import annotations

import json

from kestrel_docs_assistant.domain.audit import AuditLog, verify_chain


def _write_three(path):
    log = AuditLog(path)
    for i in range(3):
        log.append("ask", actor=f"user{i}", question=f"q{i}")
    return path


def test_intact_chain_verifies(tmp_path):
    result = verify_chain(_write_three(tmp_path / "audit.jsonl"))
    assert result.ok and result.records == 3


def test_editing_a_record_is_detected(tmp_path):
    path = _write_three(tmp_path / "audit.jsonl")
    lines = path.read_text().splitlines()
    record = json.loads(lines[1])
    record["actor"] = "someone-else"  # cover my tracks
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n")
    result = verify_chain(path)
    assert not result.ok and result.first_bad_seq == 2


def test_deleting_a_record_is_detected(tmp_path):
    path = _write_three(tmp_path / "audit.jsonl")
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert not verify_chain(path).ok


def test_log_resumes_chain_after_restart(tmp_path):
    path = _write_three(tmp_path / "audit.jsonl")
    AuditLog(path).append("ask", actor="after-restart")  # new process, same file
    result = verify_chain(path)
    assert result.ok and result.records == 4
