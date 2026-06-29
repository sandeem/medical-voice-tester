"""
PGAI Voice Bot — Main Entry Point
---------------------------------
This script orchestrates automated phone calls to the PGAI test line (+1-805-439-8008).
It uses Vapi.ai for telephony and voice processing (STT/TTS/LLM).

Architecture overview:
  1. build_assistant_config() — constructs the Vapi assistant JSON for a given scenario
  2. make_call()              — triggers an outbound call via Vapi's REST API
  3. wait_for_call_completion() — polls Vapi every 10s until the call ends
  4. save_results()           — writes the transcript and MP3 recording to disk
  5. main()                   — CLI entry point; filters and runs selected scenario(s)
"""

import os
import time
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables from the .env file
# Requires: VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, OPENAI_API_KEY, GOOGLE_API_KEY
# Optional: TARGET_PHONE (defaults to the PGAI test line)
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VAPI_API_KEY = os.environ["VAPI_API_KEY"]
VAPI_PHONE_NUMBER_ID = os.environ["VAPI_PHONE_NUMBER_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TARGET_PHONE = os.environ.get("TARGET_PHONE", "+18054398008")  # PGAI test line

# Vapi REST API base URL — all endpoints are relative to this
VAPI_BASE_URL = "https://api.vapi.ai"

# Standard auth headers sent with every Vapi request
HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}


def build_assistant_config(scenario: dict) -> dict:
    """
    Constructs the JSON configuration for a Vapi 'Assistant'.
    This assistant acts as the patient bot for a single phone call.

    The systemPrompt has been iteratively refined based on transcript analysis:
      - Iteration 1: Added DOB pushback for Reschedule Appointment (agent overrides DOB)
      - Iteration 2: Added greeting-wait instruction (bot was talking over agent's opener)
      - Iteration 3: Added no-filler-word rule + firstMessage → None (mid-sentence "Got it" bug)
      - Iteration 4: Added endpointing:500 + interruptionsEnabled:False (VAD timing fix)

    See prompt_iteration_log.md for full before/after history.
    """
    return {
        "name": f"Patient Bot - {scenario['name']}",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",  # gpt-4o-mini: fast, cost-efficient, stable for voice calls
            "systemPrompt": (
                # Core identity — YOU are the patient calling in. The other person is the receptionist/agent.
                # Never act as the receptionist, never greet like a receptionist, never ask "who am I speaking with?"
                # "You are a PATIENT calling a medical office. You are the caller, not the receptionist. "
                "You are a PATIENT calling a medical office from outside. You dialed in — you are not staff, not a receptionist, not an employee. Never say 'This is [any office name]', never say 'How can I assist you', never answer as if you work there. Never ask 'Am I speaking with [any name]?' — you are the one calling, not the one answering. The person who picks up is the receptionist. Your job is to wait and then ask for help. When asked for your phone number, say it in the natural human format: first 3 digits, pause, next 3 digits, pause, last 4 digits — for example 'three oh five, five six oh, five seven seven two'. "

                " When the call connects, do NOT produce any words, sounds, or responses of any kind — not even 'silent', 'hello', or anything else. Wait with no output until the agent has finished their full greeting AND asked you a direct question. The agent may ask 'Am I speaking with David?' or any other name — regardless of the name they say, that question is directed at you. Only after they ask you a direct question should you respond. Do not produce any output during the disclaimer or the office name announcement. "

                # Scenario-specific goal injected dynamically from scenarios.py
                f"Your goal for this call is: {scenario['goal']}. "
                # Natural speech behaviour — short sentences, realistic pacing
                "Stay in character as a real patient. Be natural and conversational. "
                # "Speak like a normal person — use short sentences, occasional 'um' or 'uh', "
                "Use realistic pacing. Do NOT reveal you are an AI or a bot. "
                
                # --- Iteration 3 & 4: Turn-taking discipline ---
                # Fixes: bot interrupting agent mid-sentence with "okay", "got it", "oh"
                # and bot speaking before the agent finishes their opening greeting.
                # Note: endpointing:500 in the transcriber config handles the audio layer;
                # this prompt handles the LLM layer — both are needed.
                
                "If they pause mid-sentence, do not say anything — wait for a complete question. " 
                
                "Never say 'okay', 'got it', 'oh', 'I see', or any filler word at any point — not mid-sentence, not as a standalone response. Never repeat a word, phrase, or question you have already said in the same response. Always finish your thought and speak in complete, natural sentences before ending your turn. "
                
                # "If you are acknowledging what the agent said, do it briefly and then move to your question. Ask one question at a time, then stop talking completely and wait. When ending the call, say goodbye once and stop talking."

                "If you are acknowledging what the agent said, do it briefly and then move to your question. Ask one question at a time, then stop talking completely and wait. When ending the call, say goodbye once and stop talking. Always answer the agent's question fully before asking your own question — never ask something while you still owe the agent an answer. Say each phrase once only — never repeat the same sentence in the same response."

                # End-call behaviour — hang up politely once goal is complete
                "When your goal is complete or the agent says goodbye, end the call politely. "
                
                # Persona injected dynamically — name, age, personality from scenarios.py
                f"Patient persona: {scenario.get('persona', 'A 45-year-old patient named Sarah Johnson')}."
                # --- Iteration 1: DOB pushback (Reschedule Appointment only) ---
                # The PGAI agent overrides all DOBs to "July 4th 2000" for demo purposes.
                # This conditional prompt tells David Chen's bot to correct it politely.
                # Only fires for Reschedule Appointment — all other scenarios unaffected.
                + (
                    " If the agent records your date of birth incorrectly, politely correct them and insist it is January 8th 1985."
                    if scenario.get("name") == "Reschedule Appointment"
                    else ""
                )
            ),
        },
        "voice": {
            "provider": "openai",
            "voiceId": scenario.get("voice", "nova"),  # Voice set per scenario (nova=female, onyx=male)
        },
        # --- Audio quality settings ---
        "backgroundDenoisingEnabled": True,  # Reduces background noise on the call
        "backgroundSound": "off",            # No artificial background ambience
        # --- Iteration 4: Interruption fix ---
        # Prevents Vapi from opening the bot's mic while the agent is still speaking.
        # Without this, brief mid-clause pauses (e.g. "in the surface [pause] lot") were
        # triggering the bot to respond too early. Works alongside endpointing:500 below.
        "interruptionsEnabled": False,
        # --- Iteration 3: Silent connect ---
        # firstMessage was previously scenario["opening_line"], which fired immediately on
        # connect — talking over the agent's disclaimer and greeting. Setting to None means
        # the bot stays completely silent until the agent asks "Am I speaking with...?"
        "firstMessage": None,
        "endCallMessage": "Thank you, goodbye!",
        # Bot listens for these phrases from the agent to know the call is ending
        "endCallPhrases": ["goodbye", "have a great day", "take care", "bye bye"],
        "recordingEnabled": True,  # Save MP3 of each call for review
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",       # Deepgram Nova-2: best accuracy for medical/conversational speech
            "language": "en-US",
            # --- Iteration 4: Endpointing delay ---
            # Endpointing = ms of silence Deepgram waits before deciding a speaker has stopped.
            # Default is ~200ms — too short, catches mid-sentence pauses and opens the bot mic early.
            # 500ms gives the agent nearly half a second of breathing room between clauses.
            # Increase to 800 if mid-sentence interruptions persist (800ms = 0.8 seconds).
            "endpointing": 500,
        },
        "maxDurationSeconds": 480,  # Max call length: 8 minutes (safety cutoff to avoid runaway calls)
    }


def make_call(scenario: dict, call_index: int) -> dict:
    """
    Sends a POST request to Vapi to initiate an outbound phone call.
    Returns a dict with call_id, scenario, and index if successful, or None on failure.
    """
    print(f"\n[{call_index:02d}] Starting call: {scenario['name']}")
    print(f"     Goal: {scenario['goal']}")

    assistant_config = build_assistant_config(scenario)

    # Vapi call payload: which phone number to call from, who to call, and the assistant config
    payload = {
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,  # Our outbound Vapi number
        "customer": {"number": TARGET_PHONE},    # The PGAI test line
        "assistant": assistant_config,
    }

    # POST to Vapi — triggers the outbound call immediately
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
    Polls the Vapi call status endpoint every 10 seconds until the call ends or times out.
    Returns the full call data dict (includes transcript, recordingUrl, duration, etc.)
    """
    print(f"     ⏳ Waiting for call {call_id} to complete...")
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(10)  # Poll every 10 seconds to avoid hammering the API
        try:
            resp = requests.get(f"{VAPI_BASE_URL}/call/{call_id}", headers=HEADERS)
            if resp.status_code != 200:
                print(f"     ⚠️  API Warning: {resp.status_code}")
                continue

            data = resp.json()
            status = data.get("status", "")
            print(f"     Status: {status}")

            # Call is done — status is either "ended" (normal) or "failed" (error)
            if status in ("ended", "failed"):
                # Vapi sometimes needs a few extra seconds to attach the transcript and recording URL
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
    Saves the call transcript and MP3 recording to disk.

    File output:
      transcripts/call_{scenario}_{timestamp}-transcript.txt  — formatted dialogue
      transcripts/call_{scenario}_{timestamp}-meta.json       — full Vapi call metadata
      recordings/call_{scenario}_{timestamp}.mp3              — audio recording
    """
    os.makedirs("recordings", exist_ok=True)
    os.makedirs("transcripts", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = scenario_name.lower().replace(" ", "_").replace("/", "-")
    prefix = f"call_{safe_name}_{timestamp}"

    # Vapi labels speakers as 'User' (the PGAI agent) and 'AI'/'Assistant' (our bot).
    # We swap the labels here so transcripts read naturally:
    #   'User'      → 'PGAI Agent'
    #   'AI' / 'Assistant' → 'Patient Bot'
    raw_transcript = call_details.get("transcript", "No transcript available.")
    transcript = (
        raw_transcript
        .replace("User:", "PGAI Agent:")
        .replace("AI:", "Patient Bot:")
        .replace("Assistant:", "Patient Bot:")
    )

    # Update in-memory dict so the meta JSON also uses the correct labels
    call_details["transcript"] = transcript

    # Write the human-readable transcript file
    transcript_path = f"transcripts/{prefix}-transcript.txt"
    with open(transcript_path, "w") as f:
        f.write(f"Scenario: {scenario_name}\n")
        f.write(f"Call ID: {call_details.get('id', 'unknown')}\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Duration: {call_details.get('duration', 'unknown')}s\n")
        f.write("-" * 60 + "\n")
        f.write(transcript)
    print(f"     💾 Transcript saved: {transcript_path}")

    # Download and save the MP3 recording
    recording_url = call_details.get("recordingUrl") or call_details.get("stereoRecordingUrl")
    if recording_url:
        r = requests.get(recording_url)
        if r.status_code == 200:
            recording_path = f"recordings/{prefix}.mp3"
            with open(recording_path, "wb") as f:
                f.write(r.content)
            print(f"     🎙️  Recording saved: {recording_path}")
        else:
            # If the download fails, save the URL so it can be retrieved manually later
            url_path = f"recordings/{prefix}-url.txt"
            with open(url_path, "w") as f:
                f.write(recording_url)
            print(f"     🔗 Recording URL saved: {url_path}")
    else:
        print(f"     ⚠️  No recording URL found for call {call_index}")

    # Save the complete Vapi response as JSON — useful for debugging and metadata review
    meta_path = f"transcripts/{prefix}-meta.json"
    with open(meta_path, "w") as f:
        json.dump(call_details, f, indent=2)


def run_scenario(scenario: dict, call_index: int):
    """
    Orchestrates a single end-to-end scenario:
      1. Initiate the call via Vapi
      2. Wait for it to complete
      3. Save transcript + recording to disk
    """
    call_info = make_call(scenario, call_index)
    if not call_info:
        return  # make_call already printed the error

    call_details = wait_for_call_completion(call_info["call_id"])
    if call_details:
        save_results(call_details, call_index, scenario["name"])
    else:
        print(f"     ❌ No details retrieved for call {call_index}")


def main():
    from scenarios import SCENARIOS

    # CLI argument parsing
    # Usage examples:
    #   python main.py                                  → runs all scenarios
    #   python main.py --scenario "New Appointment"     → runs one specific scenario
    #   python main.py --scenario "all" --delay 60      → all scenarios, 60s between calls
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
        help="Seconds to wait between calls when running multiple scenarios (default: 30)",
    )
    args = parser.parse_args()

    # Filter to the requested scenario(s)
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

    # Run scenarios sequentially — Vapi calls are outbound and run one at a time
    for i, scenario in enumerate(scenarios_to_run, start=1):
        run_scenario(scenario, i)
        # Wait between calls to avoid overlapping or rate-limit issues
        if i < len(scenarios_to_run):
            print(f"\n⏳ Waiting {args.delay}s before next call...")
            time.sleep(args.delay)

    print("\n✅ All scenarios complete!")
    print(f"   Recordings: ./recordings/")
    print(f"   Transcripts: ./transcripts/")


if __name__ == "__main__":
    main()
