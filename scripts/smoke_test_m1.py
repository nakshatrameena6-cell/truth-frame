"""End-to-End Live HTTP API Smoke Test for PRD Milestone M1.

Starts a live uvicorn server in a subprocess, executes real HTTP requests
against the endpoints, verifies response contracts, determinism, provenance safety,
error handling, and measures roundtrip latency.
"""
from __future__ import annotations

import io
import os
import struct
import subprocess
import sys
import time
import wave

import httpx

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def generate_wav(samples: list[int], rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def run_smoke_test() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    # 1. Start live uvicorn server in background subprocess
    print(f"[1/8] Starting live backend on {BASE_URL}...")
    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "audio_detection.api.app:app",
            "--host",
            SERVER_HOST,
            "--port",
            str(SERVER_PORT),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    results = {}

    try:
        # 2. Wait for server readiness via /health
        print("[2/8] Waiting for server readiness at /health...")
        ready = False
        for attempt in range(25):
            try:
                r = client.get("/health")
                if r.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.4)

        if not ready:
            raise RuntimeError("Backend server failed to start within timeout.")
        print("  [OK] Server is ready. /health returned HTTP 200.")

        # 3. Test GET /health contract
        health_data = client.get("/health").json()
        assert health_data.get("status") == "ok"
        assert health_data.get("model_version") == "m1-stub"
        print(f"  [OK] Model version verified: {health_data.get('model_version')}")

        # 4. End-to-End POST /v1/audio/score -> 202 Accepted
        print("[3/8] Executing POST /v1/audio/score with real WAV payload...")
        audio_bytes = generate_wav([1000, -1000, 500, -500] * 4000)

        t0 = time.perf_counter()
        post_resp = client.post(
            "/v1/audio/score",
            files={"file": ("fraud_investigation_call.wav", audio_bytes, "audio/wav")},
            data={"operating_point": "fpr_1pct", "language": "hi-en_codeswitch"},
        )
        post_latency_ms = (time.perf_counter() - t0) * 1000.0

        assert post_resp.status_code == 202, f"Expected 202, got {post_resp.status_code}: {post_resp.text}"
        post_json = post_resp.json()
        job_id = post_json.get("job_id")
        assert job_id and job_id.startswith("scr_"), f"Invalid job_id: {job_id}"
        print(f"  [OK] Received HTTP 202 Accepted. job_id = {job_id} (latency: {post_latency_ms:.2f}ms)")

        # 5. End-to-End GET /v1/audio/score/{job_id} -> 200 OK
        print(f"[4/8] Executing GET /v1/audio/score/{job_id} to retrieve result...")
        t1 = time.perf_counter()
        get_resp = client.get(f"/v1/audio/score/{job_id}")
        get_latency_ms = (time.perf_counter() - t1) * 1000.0

        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        data = get_resp.json()
        print(f"  [OK] Received HTTP 200 OK (latency: {get_latency_ms:.2f}ms)")

        # 6. Validate complete PRD Section 05 Response Schema
        print("[5/8] Validating complete PRD Section 05 response schema...")
        assert data["job_id"] == job_id
        assert data["status"] == "complete"

        # Verdict validation
        verdict = data["verdict"]
        assert verdict["band"] in ["consistent_with_human", "inconclusive", "likely_synthetic"]
        assert 0.0 <= verdict["probability"] <= 1.0
        assert verdict["operating_point"] == "fpr_1pct"
        if verdict["band"] == "inconclusive":
            assert verdict["reason"] is not None
        else:
            assert verdict["reason"] is None
        print(f"  [OK] Verdict: band='{verdict['band']}', prob={verdict['probability']}, op='{verdict['operating_point']}'")

        # Conditions validation (FR-2)
        conditions = data["conditions"]
        assert conditions["effective_bandwidth_hz"] > 0
        assert isinstance(conditions["estimated_codec_chain"], list)
        assert conditions["snr_db"] > 0
        assert conditions["quality_gate"] == "passed"
        print(f"  [OK] Conditions: bandwidth={conditions['effective_bandwidth_hz']}Hz, SNR={conditions['snr_db']}dB, codecs={conditions['estimated_codec_chain']}")

        # Provenance validation (FR-7: missing credentials must never be evidence)
        provenance = data["provenance"]
        assert provenance["c2pa"] == "not_present"
        assert provenance["watermark"] == "not_present"
        assert provenance["contributed_to_verdict"] is False
        print("  [OK] Provenance safety verified: c2pa=not_present, watermark=not_present, contributed_to_verdict=False")

        # Evidence validation (FR-15)
        evidence = data["evidence"]
        assert len(evidence["signal_contributions"]) >= 3
        assert evidence["language_detected"] == "hi-en_codeswitch"
        assert evidence["model_version"] == "m1-stub"
        assert evidence["threshold_version"] == "thr-2026-09-01"
        print(f"  [OK] Evidence: model={evidence['model_version']}, threshold={evidence['threshold_version']}, signals={len(evidence['signal_contributions'])}")

        # 7. Test HTTP Determinism
        print("[6/8] Testing HTTP reproducibility on identical audio...")
        repeat_post = client.post(
            "/v1/audio/score",
            files={"file": ("fraud_investigation_call.wav", audio_bytes, "audio/wav")},
            data={"operating_point": "fpr_1pct", "language": "hi-en_codeswitch"},
        )
        assert repeat_post.status_code == 202
        repeat_job_id = repeat_post.json()["job_id"]
        repeat_data = client.get(f"/v1/audio/score/{repeat_job_id}").json()

        assert repeat_data["verdict"]["probability"] == data["verdict"]["probability"]
        assert repeat_data["verdict"]["band"] == data["verdict"]["band"]
        assert repeat_data["conditions"] == data["conditions"]
        print("  [OK] Determinism verified: identical outputs for identical audio payload.")

        # 8. Test Typed Error Handling over HTTP
        print("[7/8] Testing typed error handling over live HTTP...")
        # Missing audio
        err1 = client.post("/v1/audio/score", data={"operating_point": "fpr_1pct"})
        assert err1.status_code == 400
        assert err1.json()["error_code"] == "MISSING_AUDIO"

        # Unsupported audio
        err2 = client.post("/v1/audio/score", files={"file": ("malware.exe", b"MZ...", "application/octet-stream")})
        assert err2.status_code == 415
        assert err2.json()["error_code"] == "UNSUPPORTED_AUDIO"

        # Unknown job
        err3 = client.get("/v1/audio/score/scr_nonexistent_live_123")
        assert err3.status_code == 404
        assert err3.json()["error_code"] == "JOB_NOT_FOUND"
        print("  [OK] Typed errors verified: 400 MISSING_AUDIO, 415 UNSUPPORTED_AUDIO, 404 JOB_NOT_FOUND.")

        total_latency_ms = post_latency_ms + get_latency_ms
        print(f"[8/8] Smoke test complete. Total roundtrip latency: {total_latency_ms:.2f}ms")

        results = {
            "status": "PASS",
            "post_latency_ms": round(post_latency_ms, 2),
            "get_latency_ms": round(get_latency_ms, 2),
            "total_roundtrip_ms": round(total_latency_ms, 2),
            "job_id": job_id,
            "model_version": evidence["model_version"],
            "verdict_band": verdict["band"],
            "probability": verdict["probability"],
        }
        return results

    finally:
        client.close()
        print("Terminating test backend server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            server_process.kill()


if __name__ == "__main__":
    try:
        res = run_smoke_test()
        print("\nSMOKE TEST SUMMARY: PASS")
        print(res)
        sys.exit(0)
    except Exception as exc:
        print(f"\nSMOKE TEST SUMMARY: FAIL ({exc})", file=sys.stderr)
        sys.exit(1)
