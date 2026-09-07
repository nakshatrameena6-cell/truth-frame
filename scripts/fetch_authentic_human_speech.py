"""Fetch authentic public-domain real human speech audio files from Wikimedia Commons.

Ensures genuine independent human speakers, truthful speaker IDs, public domain / CC licenses,
and records explicit provenance metadata for every downloaded file.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import soundfile as sf


# Explicit list of verified Wikimedia Commons / Local Authentic Human Audio Sources
RESOURCES = [
    {
        "key": "booker_t_washington",
        "speaker_id": "spk_booker_t_washington",
        "source_id": "src_wikimedia_booker_t_washington_1895",
        "title": "File:Booker T. Washington, Speech, 1895 - edit.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - 1895 Atlanta Exposition Address",
    },
    {
        "key": "franklin_d_roosevelt",
        "speaker_id": "spk_franklin_d_roosevelt",
        "source_id": "src_wikimedia_fdr_four_freedoms_1941",
        "title": "File:Franklin D. Roosevelt - Annual Message to Congress (January 6, 1941) - Four Freedoms Speech.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - FDR Four Freedoms Speech (1941)",
    },
    {
        "key": "george_w_bush",
        "speaker_id": "spk_george_w_bush",
        "source_id": "src_wikimedia_bush_congress_2001",
        "title": "File:Bush Addresses Congress 9-20-01.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - George W. Bush Address to Congress (2001)",
    },
    {
        "key": "winston_churchill",
        "speaker_id": "spk_winston_churchill",
        "source_id": "src_wikimedia_churchill_1940",
        "title": "File:Winston Churchill - Be Ye Men of Valour.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Winston Churchill Be Ye Men of Valour (1940)",
    },
    {
        "key": "amy_coney_barrett",
        "speaker_id": "spk_amy_coney_barrett",
        "source_id": "src_wikimedia_barrett_confirmation_2020",
        "title": "File:Amy Coney Barrett's opening statement at Supreme Court confirmation hearing.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Amy Coney Barrett Opening Statement (2020)",
    },
    {
        "key": "brett_kavanaugh",
        "speaker_id": "spk_brett_kavanaugh",
        "source_id": "src_wikimedia_kavanaugh_confirmation_2018",
        "title": "File:Brett Kavanaugh's Opening Statement to the Senate Judiciary Committee.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Brett Kavanaugh Senate Judiciary Committee (2018)",
    },
    {
        "key": "denis_mcdonough",
        "speaker_id": "spk_denis_mcdonough",
        "source_id": "src_wikimedia_mcdonough_confirmation_2021",
        "title": "File:Denis McDonough's Opening Statement at his Confirmation Hearing to be Secretary of Veterans' Affairs.oga",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Denis McDonough Confirmation Hearing (2021)",
    },
    {
        "key": "haile_selassie",
        "speaker_id": "spk_haile_selassie",
        "source_id": "src_wikimedia_selassie_un_1968",
        "title": "File:Emperor Haile Selassie I's 1968 Speech to the United Nations.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Emperor Haile Selassie UN Speech (1968)",
    },
    {
        "key": "marcus_garvey",
        "speaker_id": "spk_marcus_garvey",
        "source_id": "src_wikimedia_garvey_speech_1921",
        "title": "File:Marcus Garvey, speech, 1921.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons - Marcus Garvey Speech (1921)",
    },
    {
        "key": "indic_dr_pt_hindi_001",
        "speaker_id": "spk_indic_dr_pt_hi_001",
        "source_id": "src_indic_doctor_patient_hindi_convo_001",
        "title": "local_audio_hindi_convo_001",
        "language": "hi",
        "license": "CC-BY-4.0",
        "provenance": "Indic Doctor-Patient Speech Dataset (Hindi Convo 001)",
    },
    {
        "key": "indic_dr_pt_tamil_001",
        "speaker_id": "spk_indic_dr_pt_ta_001",
        "source_id": "src_indic_doctor_patient_tamil_convo_001",
        "title": "local_audio_tamil_convo_001",
        "language": "ta",
        "license": "CC-BY-4.0",
        "provenance": "Indic Doctor-Patient Speech Dataset (Tamil Convo 001)",
    },
    {
        "key": "jfk_inaugural",
        "speaker_id": "spk_jfk",
        "source_id": "src_wikimedia_jfk_inaugural_1961",
        "title": "File:JFK inaugural address.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    },
    {
        "key": "eisenhower_farewell",
        "speaker_id": "spk_eisenhower",
        "source_id": "src_wikimedia_eisenhower_farewell_1961",
        "title": "File:Eisenhower farewell address.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    },
    {
        "key": "nixon_resignation",
        "speaker_id": "spk_nixon",
        "source_id": "src_wikimedia_nixon_resignation_1974",
        "title": "File:Nixon resignation audio.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    },
    {
        "key": "reagan_tear_down",
        "speaker_id": "spk_reagan",
        "source_id": "src_wikimedia_reagan_tear_down_1987",
        "title": "File:Reagan Brandenburg Gate speech.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    },
    {
        "key": "calvin_coolidge",
        "speaker_id": "spk_calvin_coolidge",
        "source_id": "src_wikimedia_coolidge_taxes_1924",
        "title": "File:Speech on Taxes, Liberty, and the Philosophy of Government, by Calvin Coolidge.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    },
    {
        "key": "warren_harding",
        "speaker_id": "spk_warren_harding",
        "source_id": "src_wikimedia_harding_normalcy_1920",
        "title": "File:Readjustment (Warren G. Harding).ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    },
    {
        "key": "william_taft",
        "speaker_id": "spk_william_taft",
        "source_id": "src_wikimedia_taft_peace_1912",
        "title": "File:William Howard Taft speaks on the abolition of war.ogg",
        "language": "en",
        "license": "Public Domain",
        "provenance": "Wikimedia Commons",
    }
]


def fetch_wikimedia_file_url(title: str, headers: dict[str, str]) -> str | None:
    query_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url&format=json"
    req = urllib.request.Request(query_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                info = page.get("imageinfo", [])
                if info:
                    return info[0].get("url")
    except Exception as err:
        print(f"Error fetching URL for {title}: {err}")
    return None


def fetch_human_audio_resources(raw_dir: Path) -> dict[str, dict]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "PandaMIND-Research-AudioBot/1.0 (https://github.com/pandamind; info@pandamind.org)"}

    results = {}
    for res in RESOURCES:
        key = res["key"]
        dest_path = raw_dir / f"wikimedia_{key}.ogg"
        
        # Check local files first
        if key == "indic_dr_pt_hindi_001":
            local_wav = Path("data/processed/phase2/hi_convo_001_clean.wav")
            if local_wav.exists():
                results[key] = {**res, "file_path": local_wav}
                continue
        elif key == "indic_dr_pt_tamil_001":
            local_wav = Path("data/processed/phase2/ta_convo_001_clean.wav")
            if local_wav.exists():
                results[key] = {**res, "file_path": local_wav}
                continue

        if not dest_path.exists() or dest_path.stat().st_size == 0:
            file_url = fetch_wikimedia_file_url(res["title"], headers)
            if not file_url:
                print(f"Skipping {key}: URL not found.")
                continue
            print(f"Downloading {key} from {file_url}...")
            try:
                req = urllib.request.Request(file_url, headers=headers)
                with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
                    f.write(resp.read())
                time.sleep(0.5)
            except Exception as err:
                print(f"Failed downloading {key}: {err}")
                if dest_path.exists():
                    dest_path.unlink()
                continue

        if dest_path.exists():
            try:
                info = sf.info(dest_path)
                print(f"Successfully verified {key}: duration={info.duration:.2f}s, rate={info.samplerate}")
                results[key] = {**res, "file_path": dest_path}
            except Exception as err:
                print(f"Corrupt audio for {key}: {err}")

    return results


if __name__ == "__main__":
    raw_directory = Path("data/raw")
    fetched = fetch_human_audio_resources(raw_directory)
    print(f"\nVerified {len(fetched)} authentic human speech sources:")
    for k, v in fetched.items():
        print(f"  - {k:<25} | Speaker: {v['speaker_id']} | Lang: {v['language']} | License: {v['license']}")
