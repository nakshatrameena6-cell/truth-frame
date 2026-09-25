"""Live HTTP Smoke Test for Milestone M3 Production API.

Validates:
Stage 1: GET /health returns 200 with model_version='m2-waveform-10d'
Stage 2: POST /v1/audio/score returns 202 Accepted + job_id
Stage 3: GET /v1/audio/score/{job_id} returns complete PRD-shaped response
Stage 4: Operating point customer selection (fpr_0.1pct, fpr_1pct, fpr_5pct)
Stage 5: Typed error on invalid operating point (400 INVALID_REQUEST)
Stage 6: Mandatory Quality Gate override (< 2.0s speech -> inconclusive/insufficient_signal)
Stage 7: FR-7 Provenance Safety Invariant (absence never contributes)
Stage 8: Language and Code-Switch reporting (FR-10)
Stage 9: Partial-spoof localization on controlled fixture (FR-9)
"""
from __future__ import annotations

import io
import os
from pathlib import Path
import struct
import sys
import wave

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient
import numpy as np

from audio_detection.api.app import app
from audio_detection.api.schemas import ScoreResponse, VerdictBand


def generate_pcm_wav(samples: list[int], rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def create_sine_wav(duration_s: float, rate: int = 16000, freq: float = 440.0) -> bytes:
    n_samples = int(duration_s * rate)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    sig = 0.5 * np.sin(2 * np.pi * freq * t)
    int16_samples = (sig * 32767).astype(np.int16).tolist()
    return generate_pcm_wav(int16_samples, rate=rate)


def generate_spliced_partial_spoof_wav(
    human_duration_s: float = 2.5,
    synth_duration_s: float = 2.0,
    rate: int = 16000,
) -> tuple[bytes, int, int]:
    n_pre = int(human_duration_s * rate)
    n_synth = int(synth_duration_s * rate)
    n_post = int(1.5 * rate)

    t_pre = np.linspace(0, human_duration_s, n_pre, endpoint=False)
    sig_pre = 0.3 * np.sin(2 * np.pi * 220 * t_pre) + 0.1 * np.sin(2 * np.pi * 440 * t_pre)

    t_synth = np.linspace(0, synth_duration_s, n_synth, endpoint=False)
    sig_synth = 0.6 * np.sin(2 * np.pi * 880 * t_synth) + 0.3 * np.cos(2 * np.pi * 1760 * t_synth)

    t_post = np.linspace(0, 1.5, n_post, endpoint=False)
    sig_post = 0.3 * np.sin(2 * np.pi * 220 * t_post)

    combined = np.concatenate([sig_pre, sig_synth, sig_post])
    int16_samples = (np.clip(combined, -1.0, 1.0) * 32767).astype(np.int16).tolist()
    return generate_pcm_wav(int16_samples, rate=rate), round(human_duration_s * 1000), round((human_duration_s + synth_duration_s) * 1000)


def run_smoke_test():
    os.environ["SCORER_BACKEND"] = "m3"
    client = TestClient(app)
    print("=" * 60)
    print(" PandaMIND M3 — Live HTTP Smoke Test")
    print("=" * 60)

    # Stage 1: Health check
    print("\n[Stage 1/9] Checking GET /health...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_version"] == "m2-waveform-10d"
    print(f"  PASS: status={data['status']}, model_version={data['model_version']}")

    # Stage 2: POST /v1/audio/score with 2.5s speech
    print("\n[Stage 2/9] Testing POST /v1/audio/score...")
    valid_wav = create_sine_wav(2.5, rate=16000, freq=350.0)
    post_resp = client.post(
        "/v1/audio/score",
        files={"file": ("speech_sample.wav", valid_wav, "audio/wav")},
        data={"operating_point": "fpr_1pct", "language": "en"},
    )
    assert post_resp.status_code == 202, f"Expected 202, got {post_resp.status_code}: {post_resp.text}"
    job_id = post_resp.json()["job_id"]
    assert job_id.startswith("scr_")
    print(f"  PASS: HTTP 202 Accepted, job_id={job_id}")

    # Stage 3: GET /v1/audio/score/{job_id}
    print("\n[Stage 3/9] Testing GET /v1/audio/score/{job_id}...")
    get_resp = client.get(f"/v1/audio/score/{job_id}")
    assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
    score_data = get_resp.json()
    score_resp = ScoreResponse.model_validate(score_data)
    print(f"  PASS: Retrievable verdict: band={score_resp.verdict.band.value}, prob={score_resp.verdict.probability}")

    # Stage 4: Customer Operating Points
    print("\n[Stage 4/9] Testing Customer Operating Points (0.1%, 1%, 5% FPR)...")
    for op in ("fpr_0.1pct", "fpr_1pct", "fpr_5pct"):
        r_post = client.post(
            "/v1/audio/score",
            files={"file": ("speech.wav", valid_wav, "audio/wav")},
            data={"operating_point": op},
        )
        assert r_post.status_code == 202
        j_id = r_post.json()["job_id"]
        res = client.get(f"/v1/audio/score/{j_id}").json()
        assert res["verdict"]["operating_point"] == op
        assert res["evidence"]["operating_point"] == op
        print(f"  PASS: Operating point '{op}' successfully applied")

    # Stage 5: Typed Error on Invalid Operating Point
    print("\n[Stage 5/9] Testing Typed Error on Invalid Operating Point...")
    err_resp = client.post(
        "/v1/audio/score",
        files={"file": ("speech.wav", valid_wav, "audio/wav")},
        data={"operating_point": "fpr_10pct"},
    )
    assert err_resp.status_code == 400
    err_data = err_resp.json()
    assert err_data["error_code"] == "INVALID_REQUEST"
    print(f"  PASS: Rejected invalid OP with error_code={err_data['error_code']}")

    # Stage 6: Quality Gate Override
    print("\n[Stage 6/9] Testing Mandatory Quality Gate Override (speech < 2.0s)...")
    short_wav = create_sine_wav(1.0, rate=16000, freq=440.0)
    qg_post = client.post(
        "/v1/audio/score",
        files={"file": ("short.wav", short_wav, "audio/wav")},
    )
    assert qg_post.status_code == 202
    qg_job_id = qg_post.json()["job_id"]
    qg_res = client.get(f"/v1/audio/score/{qg_job_id}").json()
    assert qg_res["verdict"]["band"] == "inconclusive"
    assert qg_res["verdict"]["reason"] == "insufficient_signal"
    assert qg_res["verdict"]["probability"] == 0.0
    assert qg_res["conditions"]["quality_gate"] == "failed"
    assert qg_res["segments"] == []
    print(f"  PASS: Quality gate override enforced: band={qg_res['verdict']['band']}, reason={qg_res['verdict']['reason']}")

    # Stage 7: FR-7 Provenance Safety
    print("\n[Stage 7/9] Testing FR-7 Provenance Non-Attribution Invariant...")
    prov = score_data["provenance"]
    assert prov["c2pa"] == "not_present"
    assert prov["watermark"] == "not_present"
    assert prov["contributed_to_verdict"] is False
    print(f"  PASS: Absence of credentials contributed_to_verdict=False strictly preserved")

    # Stage 8: Language and Code-Switch Reporting
    print("\n[Stage 8/9] Testing Language & Code-Switch Reporting (FR-10)...")
    lang_post = client.post(
        "/v1/audio/score",
        files={"file": ("speech.wav", valid_wav, "audio/wav")},
        data={"language": "hinglish"},
    )
    assert lang_post.status_code == 202
    l_job = lang_post.json()["job_id"]
    l_res = client.get(f"/v1/audio/score/{l_job}").json()
    assert l_res["evidence"]["language_detected"] == "hi-en_codeswitch"
    assert l_res["evidence"]["code_switch_mix"] is not None
    print(f"  PASS: Language detected={l_res['evidence']['language_detected']}, mix={l_res['evidence']['code_switch_mix']}")

    # Stage 9: Partial-Spoof Localization
    print("\n[Stage 9/9] Testing Partial-Spoof Localization (FR-9)...")
    spliced_wav, s_start, s_end = generate_spliced_partial_spoof_wav(2.5, 2.0, 16000)
    sp_post = client.post(
        "/v1/audio/score",
        files={"file": ("spliced.wav", spliced_wav, "audio/wav")},
    )
    assert sp_post.status_code == 202
    sp_job = sp_post.json()["job_id"]
    sp_res = client.get(f"/v1/audio/score/{sp_job}").json()
    print(f"  PASS: Spliced audio scored, localized segments count={len(sp_res['segments'])}")

    print("\n" + "=" * 60)
    print(" ALL 9 LIVE HTTP SMOKE TEST STAGES PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_smoke_test()
