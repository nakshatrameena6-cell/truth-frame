"""End-to-End Live HTTP API Smoke Test for PRD Milestone M2.

Starts a live uvicorn server running the real M2 baseline model, executes real HTTP requests
against all endpoints, verifies the PRD contract, determinism, provenance safety,
error handling, and measures roundtrip live inference latency.
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
SERVER_PORT = 8766
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
    env["SCORER_BACKEND"] = "m2"

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

    try:
        # Wait for server readiness
        ready = False
        for attempt in range(30):
            try:
                r = httpx.get(f"{BASE_URL}/health", timeout=1.0)
                if r.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.5)

        if not ready:
            raise RuntimeError("Live server failed to start within 15 seconds.")

        print("[2/8] Server is live and healthy.")

        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # 2. Health endpoint check
            health_res = client.get("/health").json()
            print(f"      Health check: status={health_res['status']}, model={health_res['model_version']}")
            assert health_res["model_version"] == "m2-waveform-10d", f"Expected m2-waveform-10d, got {health_res['model_version']}"

            # 3. Create test audio
            test_wav_1 = generate_wav([int(10000 * (i % 2 * 2 - 1)) for i in range(16000)], rate=16000)
            test_wav_2 = generate_wav([int(5000 * (i % 4 - 2)) for i in range(16000)], rate=16000)

            # 4. POST /v1/audio/score with real M2 inference
            print("[3/8] Submitting audio for scoring (POST /v1/audio/score)...")
            t_start = time.perf_counter()
            post_resp = client.post(
                "/v1/audio/score",
                files={"file": ("recording.wav", test_wav_1, "audio/wav")},
                data={"operating_point": "fpr_1pct", "language": "en"},
            )
            t_post = time.perf_counter() - t_start
            assert post_resp.status_code == 202, f"Expected 202, got {post_resp.status_code}: {post_resp.text}"
            job_id = post_resp.json()["job_id"]
            print(f"      Job accepted: job_id={job_id} ({t_post*1000:.2f} ms)")

            # 5. GET /v1/audio/score/{job_id}
            print(f"[4/8] Retrieving scoring verdict (GET /v1/audio/score/{job_id})...")
            t_get_start = time.perf_counter()
            get_resp = client.get(f"/v1/audio/score/{job_id}")
            t_get = time.perf_counter() - t_get_start
            assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
            result = get_resp.json()
            print(f"      Retrieved in {t_get*1000:.2f} ms")
            print(f"      Verdict: {result['verdict']['band']} (prob={result['verdict']['probability']})")
            print(f"      Evidence: model={result['evidence']['model_version']}")

            # 6. Verify FR-7 Provenance Safety
            print("[5/8] Verifying FR-7 Provenance Safety Invariant...")
            prov = result["provenance"]
            assert prov["c2pa"] == "not_present"
            assert prov["watermark"] == "not_present"
            assert prov["contributed_to_verdict"] is False
            print("      FR-7 verified: contributed_to_verdict == False")

            # 7. Verify Determinism
            print("[6/8] Verifying deterministic scoring...")
            post_resp_b = client.post(
                "/v1/audio/score",
                files={"file": ("recording.wav", test_wav_1, "audio/wav")},
                data={"operating_point": "fpr_1pct", "language": "en"},
            )
            job_id_b = post_resp_b.json()["job_id"]
            result_b = client.get(f"/v1/audio/score/{job_id_b}").json()
            assert result["verdict"]["probability"] == result_b["verdict"]["probability"]
            assert result["verdict"]["band"] == result_b["verdict"]["band"]
            print("      Determinism verified: exact match on identical inputs")

            # 8. Error handling
            print("[7/8] Verifying typed error handling...")
            err1 = client.post("/v1/audio/score", files={"file": ("empty.wav", b"", "audio/wav")})
            assert err1.status_code == 400
            assert err1.json()["error_code"] == "EMPTY_AUDIO"

            err2 = client.post(
                "/v1/audio/score",
                files={"file": ("test.wav", test_wav_1, "audio/wav")},
                data={"operating_point": "invalid_op"},
            )
            assert err2.status_code == 400
            assert err2.json()["error_code"] == "INVALID_REQUEST"
            print("      Typed errors verified: EMPTY_AUDIO (400), INVALID_REQUEST (400)")

            # Latency benchmark
            print("[8/8] Measuring live end-to-end scoring latency...")
            latencies = []
            for _ in range(5):
                t0 = time.perf_counter()
                p = client.post(
                    "/v1/audio/score",
                    files={"file": ("bench.wav", test_wav_2, "audio/wav")},
                )
                jid = p.json()["job_id"]
                client.get(f"/v1/audio/score/{jid}")
                latencies.append((time.perf_counter() - t0) * 1000)

            avg_lat = sum(latencies) / len(latencies)
            p95_lat = sorted(latencies)[int(0.95 * len(latencies))]
            print(f"      Roundtrip latency: avg={avg_lat:.2f} ms, p95={p95_lat:.2f} ms")

            print("\n=======================================================")
            print(" M2 LIVE HTTP SMOKE TEST: ALL 8 STAGES PASSED!")
            print("=======================================================")

            return {
                "status": "PASS",
                "avg_latency_ms": round(avg_lat, 2),
                "p95_latency_ms": round(p95_lat, 2),
                "model_version": result["evidence"]["model_version"],
                "verdict_band": result["verdict"]["band"],
                "probability": result["verdict"]["probability"],
            }

    finally:
        server_process.terminate()
        server_process.wait(timeout=5.0)


if __name__ == "__main__":
    run_smoke_test()
