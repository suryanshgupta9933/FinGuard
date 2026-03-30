"""
tests/test_audit.py
====================
Tests for the GuardTrace audit system.

Covers:
  - GuardTrace is emitted on every invocation (pass + block)
  - ScannerTrace is populated per scanner
  - block_stage is correctly set ("input" vs "output")
  - In-process query API: traces, get_trace, violations
  - MemoryBackend stores and retrieves traces
  - FileBackend writes valid NDJSON
  - input_hash is never the raw prompt
  - Metadata allowlist filtering
"""
import asyncio
import json
import os
import pytest
import pytest_asyncio
from pathlib import Path

from finguard import FinGuard, GuardTrace, ScannerTrace, GuardRequest
from finguard.audit.backends.memory import MemoryBackend
from finguard.audit.backends.file import FileBackend
from finguard.audit.trace import GuardTrace as GuardTraceModel


# ── Helpers ───────────────────────────────────────────────────────────────────

SAFE_POLICY = {
    "policy_id": "audit_safe",
    "risk_level": "low",
    "injection": {"enabled": True},
    "audit": {
        "backend": "memory",
        "emit_traces": True,
        "redact_input": True,
    },
}

BLOCK_POLICY = {
    "policy_id": "audit_block",
    "risk_level": "high",
    "injection": {"enabled": True},
    "audit": {
        "backend": "memory",
        "emit_traces": True,
        "redact_input": True,
    },
}


async def safe_llm(p: str) -> str:
    return "Safe response from LLM"


# ── GuardTrace schema tests ───────────────────────────────────────────────────

class TestGuardTraceSchema:
    def test_trace_id_is_uuid(self):
        t = GuardTraceModel(
            policy_id="test", input_hash="abc", input_length=10,
            is_safe=True, action="pass", total_latency_ms=5.0
        )
        assert len(t.trace_id) == 36
        assert t.trace_id.count("-") == 4

    def test_fingerprint_is_not_reversible(self):
        raw = "My secret prompt"
        fp = GuardTraceModel.fingerprint(raw)
        assert raw not in fp
        assert len(fp) == 16

    def test_fingerprint_is_deterministic(self):
        text = "Hello FinGuard"
        assert GuardTraceModel.fingerprint(text) == GuardTraceModel.fingerprint(text)

    def test_to_log_dict_is_flat(self):
        t = GuardTraceModel(
            policy_id="retail", input_hash="abc123", input_length=50,
            is_safe=False, action="block", total_latency_ms=120.0,
            block_stage="input",
            input_scanners=[
                ScannerTrace(scanner="prompt_injection", stage="input",
                             triggered=True, score=0.95, latency_ms=80.0)
            ]
        )
        d = t.to_log_dict()
        # Should be a flat dict — no nested lists except triggered/skipped
        assert isinstance(d, dict)
        assert d["is_safe"] is False
        assert d["block_stage"] == "input"
        assert "prompt_injection" in d["triggered_scanners"]
        assert d["input_scanner_count"] == 1

    def test_summary_contains_key_info(self):
        t = GuardTraceModel(
            policy_id="test", input_hash="abc", input_length=10,
            is_safe=True, action="pass", total_latency_ms=42.5
        )
        s = t.summary()
        assert "PASS" in s
        assert "test" in s
        assert "42.5ms" in s


# ── ScannerTrace tests ────────────────────────────────────────────────────────

class TestScannerTrace:
    def test_triggered_false_by_default(self):
        s = ScannerTrace(scanner="topic_boundary", stage="input",
                         triggered=False, latency_ms=5.0)
        assert s.triggered is False
        assert s.skipped is False
        assert s.skip_reason is None

    def test_skipped_trace_has_reason(self):
        s = ScannerTrace(scanner="prompt_injection", stage="input",
                         triggered=False, latency_ms=0.1,
                         skipped=True, skip_reason="TimeoutError: took 5000ms")
        assert s.skipped is True
        assert "Timeout" in s.skip_reason


# ── MemoryBackend tests ───────────────────────────────────────────────────────

class TestMemoryBackend:
    def _make_trace(self, policy_id="test", is_safe=True):
        return GuardTraceModel(
            policy_id=policy_id, input_hash="x", input_length=5,
            is_safe=is_safe, action="pass" if is_safe else "block",
            total_latency_ms=10.0
        )

    def test_emit_and_retrieve(self):
        mem = MemoryBackend()
        t = self._make_trace()
        mem.emit(t)
        assert len(mem) == 1
        assert mem.get_by_id(t.trace_id) is t

    def test_get_by_policy(self):
        mem = MemoryBackend()
        mem.emit(self._make_trace("policy_a"))
        mem.emit(self._make_trace("policy_b"))
        mem.emit(self._make_trace("policy_a"))
        assert len(mem.get_by_policy("policy_a")) == 2

    def test_get_violations_only_returns_unsafe(self):
        mem = MemoryBackend()
        mem.emit(self._make_trace(is_safe=True))
        mem.emit(self._make_trace(is_safe=False))
        violations = mem.get_violations()
        assert len(violations) == 1
        assert violations[0].is_safe is False

    def test_maxlen_circular_eviction(self):
        mem = MemoryBackend(maxlen=3)
        for i in range(5):
            mem.emit(self._make_trace())
        assert len(mem) == 3  # Oldest evicted

    def test_clear(self):
        mem = MemoryBackend()
        mem.emit(self._make_trace())
        mem.clear()
        assert len(mem) == 0


# ── FileBackend tests ─────────────────────────────────────────────────────────

class TestFileBackend:
    def test_emit_writes_ndjson(self, tmp_path):
        path = str(tmp_path / "test.ndjson")
        backend = FileBackend(path=path)
        t = GuardTraceModel(
            policy_id="file_test", input_hash="abc", input_length=10,
            is_safe=True, action="pass", total_latency_ms=5.0
        )
        backend.emit(t)
        lines = Path(path).read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["policy_id"] == "file_test"
        assert "trace_id" in parsed

    def test_emit_appends_multiple(self, tmp_path):
        path = str(tmp_path / "multi.ndjson")
        backend = FileBackend(path=path)
        for _ in range(3):
            backend.emit(GuardTraceModel(
                policy_id="p", input_hash="h", input_length=5,
                is_safe=True, action="pass", total_latency_ms=1.0
            ))
        lines = Path(path).read_text().strip().split("\n")
        assert len(lines) == 3

    def test_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / "nested" / "logs" / "out.ndjson")
        backend = FileBackend(path=path)
        backend.emit(GuardTraceModel(
            policy_id="p", input_hash="h", input_length=5,
            is_safe=True, action="pass", total_latency_ms=1.0
        ))
        assert Path(path).exists()


# ── Integration: trace emitted through FinGuard ───────────────────────────────

class TestGuardTraceIntegration:
    @pytest.mark.asyncio
    async def test_trace_attached_to_result_on_pass(self):
        guard = FinGuard(policy=SAFE_POLICY)
        req = GuardRequest(prompt="What is my account balance?")
        result = await guard(req, safe_llm)
        assert result.trace is not None
        assert isinstance(result.trace, GuardTraceModel)
        assert result.trace.is_safe is True
        assert result.trace.action == "pass"
        assert result.trace.block_stage is None

    @pytest.mark.asyncio
    async def test_input_hash_is_not_raw_prompt(self):
        guard = FinGuard(policy=SAFE_POLICY)
        prompt = "My secret financial query"
        req = GuardRequest(prompt=prompt)
        result = await guard(req, safe_llm)
        assert prompt not in result.trace.input_hash
        assert len(result.trace.input_hash) == 16  # SHA-256[:16]

    @pytest.mark.asyncio
    async def test_scanner_traces_populated(self):
        guard = FinGuard(policy=SAFE_POLICY)
        req = GuardRequest(prompt="Hello")
        result = await guard(req, safe_llm)
        # At least the injection scanner should have run
        assert len(result.trace.input_scanners) > 0
        st = result.trace.input_scanners[0]
        assert isinstance(st, ScannerTrace)
        assert st.stage == "input"

    @pytest.mark.asyncio
    async def test_block_stage_set_on_input_block(self):
        guard = FinGuard(policy={
            "policy_id": "block_test",
            "risk_level": "high",
            "pii": {"enabled": True},
            "audit": {"backend": "memory"},
        })
        # PAN card in input should block at input stage
        req = GuardRequest(prompt="My PAN is ABCDE1234F, transfer funds")
        async def dummy_llm(p): return "OK"
        result = await guard(req, dummy_llm)
        if not result.is_safe:
            assert result.trace.block_stage == "input"

    @pytest.mark.asyncio
    async def test_in_process_query_api(self):
        guard = FinGuard(policy=SAFE_POLICY)
        req = GuardRequest(prompt="Check my balance")
        result = await guard(req, safe_llm)
        trace_id = result.trace.trace_id

        # Get via guard.traces
        assert any(t.trace_id == trace_id for t in guard.traces)

        # Get via guard.get_trace()
        retrieved = guard.get_trace(trace_id)
        assert retrieved is not None
        assert retrieved.trace_id == trace_id

    @pytest.mark.asyncio
    async def test_violations_list_only_has_unsafe(self):
        guard = FinGuard(policy=SAFE_POLICY)
        req = GuardRequest(prompt="Normal question")
        await guard(req, safe_llm)
        # After a safe call, violations list should be empty
        assert all(not t.is_safe for t in guard.violations)

    @pytest.mark.asyncio
    async def test_metadata_flows_into_trace(self):
        guard = FinGuard(policy={
            "policy_id": "meta_test",
            "risk_level": "low",
            "audit": {"backend": "memory"},
        })
        req = GuardRequest(
            prompt="Hello",
            metadata={"case_id": "CASE-001", "user_id": "u123"}
        )
        result = await guard(req, safe_llm)
        assert result.trace.metadata.get("case_id") == "CASE-001"
        assert result.trace.metadata.get("user_id") == "u123"

    @pytest.mark.asyncio
    async def test_metadata_allowlist_filters_keys(self):
        guard = FinGuard(policy={
            "policy_id": "allowlist_test",
            "risk_level": "low",
            "audit": {
                "backend": "memory",
                "include_metadata_keys": ["case_id"],  # Only allow case_id
            },
        })
        req = GuardRequest(
            prompt="Hello",
            metadata={"case_id": "CASE-001", "secret_field": "should_be_filtered"}
        )
        result = await guard(req, safe_llm)
        assert "case_id" in result.trace.metadata
        assert "secret_field" not in result.trace.metadata
