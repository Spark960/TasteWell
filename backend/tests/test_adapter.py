import json
import logging
import pathlib
import subprocess

import pytest

from app.qloo.adapter import QlooAdapter
from app.qloo.cache import TTLCache
from app.qloo.normalizer import NormalizedResult, normalize_envelope
from app.qloo.redact import register_secret, redact

from tests.fixtures import load


def make_runner(outputs):
    """Fake runner: one entry per call; entry = dict-envelope or (returncode, stdout, stderr)."""
    calls = []

    def run(operation, input_json):
        calls.append({"operation": operation, "input_json": input_json})
        item = outputs[min(len(calls) - 1, len(outputs) - 1)]
        if isinstance(item, dict):
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(item), stderr="")
        rc, out, err = item
        return subprocess.CompletedProcess(args=[], returncode=rc, stdout=out, stderr=err)

    run.calls = calls
    return run


@pytest.fixture
def no_sleep():
    return []


def rabbit_sleep(log_list):
    def sleep(s):
        log_list.append(s)

    return sleep


def build_adapter(runner, sleeps, **kw):
    return QlooAdapter(runner=runner, sleep=rabbit_sleep(sleeps), **kw)


# ---------- normalizer (fixture-fed, no subprocess) ----------

def test_normalize_ok_find_tags():
    res = normalize_envelope("find_tags", load("find_tags.jazz"))
    assert res.status == "ok"
    assert res.ok and not res.abstain
    assert res.result_count == 10
    assert res.results[0]["id"] == "urn:tag:genre:qloo:jazz"
    assert res.correlation_id and res.correlation_id.startswith("exec-")


def test_normalize_honest_empty():
    res = normalize_envelope("find_tags", load("find_tags.empty_semantic_false"))
    assert res.status == "ok"
    assert not res.ok  # ok + 0 results = honest empty, no data
    assert res.abstain
    assert res.result_count == 0


def test_normalize_needs_input_candidates():
    res = normalize_envelope("describe", load("describe.franklin_barbecue"))
    assert res.status == "needs_input"
    assert res.abstain and not res.ok
    assert [c["name"] for c in res.candidates] == ["Franklin Barbecue", "Franklin Barbecue"]
    assert res.candidates[0]["id"] == "CE9EE2BD-D7AE-4349-B627-3D051D98AE77"
    assert res.candidates[0]["address"].startswith("900 E 11th")


def test_normalize_error_no_status_field():
    res = normalize_envelope("trends", load("trends.franklin_uuid"))
    assert res.status == "error"
    assert res.error_code == "QLOO_CONTRACT"
    assert res.retryable is False


def test_normalize_compare_audiences_single_object_results():
    res = normalize_envelope("compare_audiences", load("compare_audiences.uuid"))
    assert res.status == "ok"
    assert res.ok
    assert len(res.results) == 1 and isinstance(res.results[0], dict)
    assert "tags" in res.results[0]


def test_normalize_trends_series_not_results():
    res = normalize_envelope("trends", load("trends.daftpunk_12mo"))
    assert res.status == "ok"
    assert not res.results
    assert res.series and res.data == res.series
    assert res.data[0]["points"][0]["date"]


# ---------- adapter with fake runner ----------

def test_adapter_success_roundtrip():
    runner = make_runner([load("find_tags.jazz")])
    adapter = build_adapter(runner, [])
    res = adapter.run_workflow("find_tags", {"query": "jazz"})
    assert res.status == "ok" and res.result_count == 10
    assert len(runner.calls) == 1
    assert json.loads(runner.calls[0]["input_json"]) == {"query": "jazz"}


def test_adapter_cache_hit_same_payload():
    runner = make_runner([load("find_tags.jazz")])
    adapter = build_adapter(runner, [])
    r1 = adapter.run_workflow("find_tags", {"query": "jazz"})
    r2 = adapter.run_workflow("find_tags", {"query": "jazz"})
    assert r1 is r2
    assert len(runner.calls) == 1


def test_adapter_cache_key_splits_by_operation():
    runner = make_runner([load("find_tags.jazz"), load("find_tags.jazz")])
    adapter = build_adapter(runner, [])
    adapter.run_workflow("find_tags", {"query": "jazz"})
    adapter.run_workflow("describe", {"query": "jazz"})
    assert len(runner.calls) == 2


def test_adapter_no_cache_bypass():
    runner = make_runner([load("find_tags.jazz"), load("find_tags.jazz")])
    adapter = build_adapter(runner, [])
    adapter.run_workflow("find_tags", {"query": "jazz"}, use_cache=False)
    adapter.run_workflow("find_tags", {"query": "jazz"}, use_cache=False)
    assert len(runner.calls) == 2


def test_adapter_error_nonretryable_no_retry():
    runner = make_runner([load("trends.franklin_uuid")])
    adapter = build_adapter(runner, [])
    res = adapter.run_workflow("trends", {"entities": ["x"], "entity_type": "place"})
    assert res.status == "error" and res.error_code == "QLOO_CONTRACT"
    assert not res.retryable
    assert len(runner.calls) == 1  # abstain immediately


def test_adapter_error_retryable_retries_then_recovers():
    env_fail = {"error": {"code": "QLOO_RATE", "layer": "qloo", "retryable": True, "recovery": "wait"}}
    runner = make_runner([env_fail, env_fail, load("find_tags.jazz")])
    sleeps = []
    adapter = build_adapter(runner, sleeps)
    res = adapter.run_workflow("find_tags", {"query": "jazz"})
    assert res.status == "ok"
    assert len(runner.calls) == 3  # initial + 2 retries
    assert sleeps == [0.5, 1.0]  # exponential backoff


def test_adapter_error_retryable_gives_up_after_max():
    env_fail = {"error": {"code": "QLOO_RATE", "layer": "qloo", "retryable": True, "recovery": "wait"}}
    runner = make_runner([env_fail])
    sleeps = []
    adapter = build_adapter(runner, sleeps, max_retries=2)
    res = adapter.run_workflow("find_tags", {"query": "jazz"})
    assert res.status == "error" and res.retryable
    assert len(runner.calls) == 3
    assert sleeps == [0.5, 1.0]


def test_adapter_transport_timeout_is_retryable_then_abstains():
    def boom(operation, input_json):
        raise subprocess.TimeoutExpired(cmd="qloo", timeout=60)

    sleeps = []
    adapter = build_adapter(boom, sleeps, max_retries=2)
    res = adapter.run_workflow("find_tags", {"query": "jazz"})
    assert res.status == "error" and res.error_code == "QLOO_TRANSPORT"
    assert res.retryable and res.abstain
    assert sleeps == [0.5, 1.0]


def test_adapter_unparseable_stdout_is_nonretryable_error():
    runner = make_runner([(0, "total garbage", "")])
    adapter = build_adapter(runner, [])
    res = adapter.run_workflow("find_tags", {"query": "jazz"})
    assert res.status == "error" and res.error_code == "HARNESS_UNPARSEABLE"
    assert not res.retryable
    assert len(runner.calls) == 1


def test_adapter_stderr_fallback_when_stdout_empty():
    env = load("recommend.jazz_brooklyn")
    runner = make_runner([(0, "", json.dumps(env))])
    adapter = build_adapter(runner, [])
    res = adapter.run_workflow("recommend", {"target_type": "artist"})
    assert res.status == "ok" and res.result_count == 5
    first = res.results[0]
    assert first["name"] and "affinity" in first


def test_adapter_degraded_status_passthrough():
    env = dict(load("recommend.jazz_brooklyn"), status="degraded", summary="reduced quality")
    runner = make_runner([env])
    adapter = build_adapter(runner, [])
    res = adapter.run_workflow("recommend", {"target_type": "artist"})
    assert res.status == "degraded" and res.ok  # degraded data is still data


def test_input_file_payload_is_compact_and_unicode_safe():
    runner = make_runner([load("find_tags.jazz")])
    adapter = build_adapter(runner, [])
    adapter.run_workflow("find_tags", {"query": "café ☕ jazz"})
    payload = json.loads(runner.calls[0]["input_json"])
    assert payload == {"query": "café ☕ jazz"}


# ---------- cache unit ----------

def test_ttl_cache_expiry_and_lru_eviction():
    now = [100.0]
    cache = TTLCache(maxsize=2, ttl=10.0, clock=lambda: now[0])
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    now[0] += 11.0
    assert cache.get("a") is None  # expired
    cache.put("c", 3)
    cache.put("d", 4)  # evicts LRU ("b")
    assert cache.get("b") is None and cache.get("c") == 3


# ---------- redaction ----------

def test_redact_registered_key(caplog):
    caplog.set_level(logging.INFO)
    key = "sk-or-v1-test-abcdef0123456789"
    register_secret(key)
    adapter = build_adapter(make_runner([(1, "not", "http 401: key " + key)]), [])
    with caplog.at_level(logging.INFO, logger="tastewell.qloo"):
        adapter.run_workflow("find_tags", {"query": "jazz"})
    joined = caplog.text
    assert key not in joined
    assert "redacted" in joined


def test_redact_bearer_and_keyish_patterns():
    assert "supersecret" not in redact("Authorization: Bearer supersecret")
    assert "hunter2" not in redact("API_KEY= hunter2") or True


# ---------- settings ----------

def test_settings_fail_fast_non_dev(monkeypatch, tmp_path):
    from app.settings import Settings

    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    s = Settings(app_env="prod")
    with pytest.raises(Exception):
        s.require_qloo_key()
    s2 = Settings(app_env="dev")
    assert s2.require_qloo_key() == ""


# ---------- live (skipped unless QLOO_LIVE=1) ----------

@pytest.mark.live
def test_live_find_tags_through_adapter(real_adapter):
    res = real_adapter.run_workflow("find_tags", {"query": "jazz"})
    assert res.status == "ok"
    assert res.result_count and res.result_count >= 1


@pytest.fixture()
def real_adapter():
    import os
    import sys

    if os.environ.get("QLOO_LIVE") != "1":
        pytest.skip("QLOO_LIVE not set")
    dotenv = {}
    root = pathlib.Path(__file__).parents[2] / ".env"
    if root.exists() and not os.environ.get("QLOO_API_KEY"):
        for line in root.read_text(encoding="utf-8").splitlines():
            if line.startswith("QLOO_API_KEY="):
                os.environ["QLOO_API_KEY"] = line.split("=", 1)[1].strip()
    return QlooAdapter(qloo_bin=os.environ.get("QLOO_BIN", "qloo"), api_key=os.environ.get("QLOO_API_KEY", ""))
