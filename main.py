"""
PGAI Voice Bot — Main Entry Point
---------------------------------
This script orchestrates automated phone calls to the PGAI test line (+1-805-439-8008).
It uses Vapi.ai for telephony and voice processing (STT/TTS/LLM).
"""

import os
import time
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables from the .env file
load_dotenv()

# Configuration: API keys and IDs from environment variables
VAPI_API_KEY = os.environ["VAPI_API_KEY"]
VAPI_PHONE_NUMBER_ID = os.environ["VAPI_PHONE_NUMBER_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TARGET_PHONE = os.environ.get("TARGET_PHONE", "+18054398008")

# Vapi API endpoint
VAPI_BASE_URL = "https://api.vapi.ai"

# Standard headers for all API requests to Vapi
HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}


def build_assistant_config(scenario: dict) -> dict:
    """
    Constructs the JSON configuration for a Vapi 'Assistant'.
    This assistant will act as the patient for a single phone call.
    """
    return {
        "name": f"Patient Bot - {scenario['name']}",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",  # Using gpt-4o-mini for speed and low cost
            "systemPrompt": (
                "You are a patient calling a medical office. "
                f"Your goal for this call is: {scenario['goal']}. "
                "Stay in character as a real patient. Be natural and conversational. "
                "Speak like a normal person — use short sentences, occasional 'um' or 'uh', "
                "and realistic pacing. Do NOT reveal you are an AI or a bot. "
                "When your goal is complete or the agent says goodbye, end the call politely. "
                " Do not speak until the other person has completely finished their turn and is clearly waiting for your response — this means they have asked a direct question or gone fully silent for several seconds. If they pause mid-sentence, do not say anything. Never say 'okay', 'got it', 'oh', or any filler word mid-sentence. When the call first connects, wait silently until the agent asks who they are speaking with before introducing yourself."
                f"Patient persona: {scenario.get('persona', 'A 45-year-old patient named Sarah Johnson')}."
                + (
                    " If the agent records your date of birth incorrectly, politely correct them and insist it is January 8th 1985."
                    if scenario.get("name") == "Reschedule Appointment"
                    else ""
                )
            ),
        },
        "voice": {
            "provider": "openai",
            "voiceId": scenario.get("voice", "nova"),  # Voice matched to patient gender
        },
        "firstMessage": None,
        "endCallMessage": "Thank you, goodbye!",
        "endCallPhrases": ["goodbye", "have a great day", "take care", "bye bye"],
        "recordingEnabled": True,
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
            "endpointing": 500,
        },
        "maxDurationSeconds": 180,  # Max call length set to 3 minutes
    }


def make_call(scenario: dict, call_index: int) -> dict:
    """
    Sends a request to Vapi to start an outbound call for a given scenario.
    """
    print(f"\n[{call_index:02d}] Starting call: {scenario['name']}")
    print(f"     Goal: {scenario['goal']}")

    assistant_config = build_assistant_config(scenario)

    payload = {
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {"number": TARGET_PHONE},
        "assistant": assistant_config,
    }

    # Trigger the call via Vapi API
    response = requests.post(
        f"{VAPI_BASE_URL}/call/phone",
        headers=HEADERS,
        json=payload,
    )

    if response.status_code not in (200, 201):
        print(f"     ❌ Call failed: {response.status_code} — {response.text}")
        return None

    call_data = response.json()
    call_id = call_data.get("id")
    print(f"     ✅ Call initiated. ID: {call_id}")
    return {"call_id": call_id, "scenario": scenario, "index": call_index}


def wait_for_call_completion(call_id: str, timeout: int = 300) -> dict:
    """
    Checks the status of the call every 10 seconds until it ends or times out.
    """
    print(f"     ⏳ Waiting for call {call_id} to complete...")
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(10)
        try:
            resp = requests.get(f"{VAPI_BASE_URL}/call/{call_id}", headers=HEADERS)
            if resp.status_code != 200:
                print(f"     ⚠️  API Warning: {resp.status_code}")
                continue

            data = resp.json()
            status = data.get("status", "")
            print(f"     Status: {status}")

            # Once the call ends (or fails), we can retrieve the transcript and recording
            if status in ("ended", "failed"):
                # Ensure the transcript and recording URL are ready before returning
                if not data.get("transcript") or not data.get("recordingUrl"):
                    time.sleep(5)
                    resp = requests.get(f"{VAPI_BASE_URL}/call/{call_id}", headers=HEADERS)
                    data = resp.json()
                return data
        except Exception as e:
            print(f"     ⚠️  Polling error: {e}")

    print(f"     ⚠️  Timeout waiting for call {call_id}")
    return {}


def save_results(call_details: dict, call_index: int, scenario_name: str):
    """
    Saves the call transcript (with role labels swapped) and the audio recording.
    """
    os.makedirs("recordings", exist_ok=True)
    os.makedirs("transcripts", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = scenario_name.lower().replace(" ", "_").replace("/", "-")
    prefix = f"call_{safe_name}_{timestamp}"

    # Vapi transcripts use 'User' and 'Assistant/AI' labels.
    # We swap them here for clarity: 'User' is the PGAI Agent, 'AI' is our Bot.
    raw_transcript = call_details.get("transcript", "No transcript available.")
    transcript = raw_transcript.replace("User:", "PGAI Agent:").replace("AI:", "Patient Bot:").replace("Assistant:", "Patient Bot:")
    
    # Update the internal transcript so the JSON metadata file also has the correct labels
    call_details["transcript"] = transcript

    # Write the formatted transcript to a text file
    transcript_path = f"transcripts/{prefix}-transcript.txt"
    with open(transcript_path, "w") as f:
        f.write(f"Scenario: {scenario_name}\n")
        f.write(f"Call ID: {call_details.get('id', 'unknown')}\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Duration: {call_details.get('duration', 'unknown')}s\n")
        # Add a clear separator before the dialogue
        f.write("-" * 60 + "\n")
        f.write(transcript)
    print(f"     💾 Transcript saved: {transcript_path}")

    # Retrieve and download the audio recording (MP3)
    recording_url = call_details.get("recordingUrl") or call_details.get("stereoRecordingUrl")
    if recording_url:
        r = requests.get(recording_url)
        if r.status_code == 200:
            recording_path = f"recordings/{prefix}.mp3"
            with open(recording_path, "wb") as f:
                f.write(r.content)
            print(f"     🎙️  Recording saved: {recording_path}")
        else:
            # If download fails, save the URL so it can be retrieved manually
            url_path = f"recordings/{prefix}-url.txt"
            with open(url_path, "w") as f:
                f.write(recording_url)
            print(f"     🔗 Recording URL saved: {url_path}")
    else:
        print(f"     ⚠️  No recording URL found for call {call_index}")

    # Save the full technical metadata as a JSON file for future reference
    meta_path = f"transcripts/{prefix}-meta.json"
    with open(meta_path, "w") as f:
        json.dump(call_details, f, indent=2)


def run_scenario(scenario: dict, call_index: int):
    """
    Executes a single test scenario and handles the data storage.
    """
    call_info = make_call(scenario, call_index)
    if not call_info:
        return

    call_details = wait_for_call_completion(call_info["call_id"])
    if call_details:
        save_results(call_details, call_index, scenario["name"])
    else:
        print(f"     ❌ No details retrieved for call {call_index}")


def main():
    from scenarios import SCENARIOS

    # Handle command-line arguments (e.g., --scenario "New Appointment")
    parser = argparse.ArgumentParser(description="PGAI Voice Bot")
    parser.add_argument(
        "--scenario",
        default="all",
        help='Scenario name to run, or "all" to run all scenarios',
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=30,
        help="Seconds to wait between calls (default: 30)",
    )
    args = parser.parse_args()

    # Filter scenarios based on user input
    if args.scenario == "all":
        scenarios_to_run = SCENARIOS
    else:
        scenarios_to_run = [s for s in SCENARIOS if s["name"].lower() == args.scenario.lower()]
        if not scenarios_to_run:
            print(f"❌ Scenario '{args.scenario}' not found.")
            print("Available scenarios:")
            for s in SCENARIOS:
                print(f"  - {s['name']}")
            return

    print(f"🤖 PGAI Voice Bot starting — {len(scenarios_to_run)} scenario(s) to run")
    print(f"📞 Target: {TARGET_PHONE}")
    print(f"⏱️  Delay between calls: {args.delay}s\n")

    # Run the selected scenarios one by one
    for i, scenario in enumerate(scenarios_to_run, start=1):
        run_scenario(scenario, i)
        # Add a delay between calls to keep things orderly
        if i < len(scenarios_to_run):
            print(f"\n⏳ Waiting {args.delay}s before next call...")
            time.sleep(args.delay)

    print("\n✅ All scenarios complete!")
    print(f"   Recordings: ./recordings/")
    print(f"   Transcripts: ./transcripts/")


if __name__ == "__main__":
    main()
