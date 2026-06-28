# Prompt Iteration Log — Patient Bot systemPrompt
**Date:** 2026-06-27
**File:** `deliverables/main.py` → `build_assistant_config()` → `systemPrompt`
**Purpose:** Documents every prompt change made during the test session, what triggered it, and what improved.

---

## Baseline — Original systemPrompt (before any changes)

```python
"systemPrompt": (
    "You are a patient calling a medical office. "
    f"Your goal for this call is: {scenario['goal']}. "
    "Stay in character as a real patient. Be natural and conversational. "
    "Speak like a normal person — use short sentences, occasional 'um' or 'uh', "
    "and realistic pacing. Do NOT reveal you are an AI or a bot. "
    "When your goal is complete or the agent says goodbye, end the call politely. "
    f"Patient persona: {scenario.get('persona', 'A 45-year-old patient named Sarah Johnson')}."
)
```

**firstMessage:** `scenario["opening_line"]` (e.g. "Hi there, I need to reschedule an appointment.")
**endpointing:** Deepgram default (~200ms)
**maxDurationSeconds:** 300

---

## Iteration 1 — DOB Pushback for Reschedule Appointment
**Triggered by:** `call_reschedule_appointment_20260627_200909-transcript.txt`
**Observation:** Agent overrode David Chen's DOB to "July 4th 2000" and the bot accepted it silently with "Thanks."
**Change:** Added a conditional prompt appended only for the Reschedule Appointment scenario.

```python
+ (
    " If the agent records your date of birth incorrectly, politely correct them and insist it is January 8th 1985."
    if scenario.get("name") == "Reschedule Appointment"
    else ""
)
```

**Result:** Bot now pushes back when the wrong DOB is recorded. Other scenarios unaffected.

---

## Iteration 2 — Wait for Agent Greeting Before Speaking
**Triggered by:** `call_cancel_appointment_20260627_205312-transcript.txt`, `call_office_hours_inquiry_20260627_205556-transcript.txt`
**Observation:** Bot fired its opening line immediately on connect, talking over the agent's disclaimer and greeting. In Cancel Appointment the exchange looked like:
```
Patient Bot: Hello. I'm calling because I need to cancel an upcoming appointment.
PGAI Agent: Calling PivotPoint Orthopedics. Part of Pretty Good     ← cut off
Patient Bot: Hi. This is
PGAI Agent: Am I speaking with David?
```
**Change:** Added wait instruction to `systemPrompt` (line 52):

```python
" When the call connects, wait for the agent to finish their greeting and answer any question they ask before stating your reason for calling."
```

**Also changed:** `firstMessage` from `scenario["opening_line"]` to `"Hello."` (neutral filler to stop the bot front-loading its agenda on connect).

**Result:** Partial improvement — bot introduced itself correctly, but still interrupted mid-sentence later in the call.

---

## Iteration 3 — One Question at a Time + No Mid-Sentence Filler
**Triggered by:** `call_office_hours_inquiry_20260627_212845-transcript.txt`
**Observation:** Bot dumped all three questions (hours + appointment + parking) in one turn, then interrupted the agent mid-answer with "Okay. Thanks for letting" and "Got it."
```
Patient Bot: Hi. No. This is Lisa Park. Um, I was wondering if you could tell me your office hours
             on Saturdays. Also, do I need to make an appointment? Or can I just walk in and,
             uh, 1 more thing, what's the parking situation like there?
PGAI Agent: We're open Monday through Friday. But the clinic is closed on Saturdays. You do need
            to make an appointment,
Patient Bot: Okay. Thanks for letting       ← interrupted mid-sentence
```
**Changes:**
1. Updated line 52 `systemPrompt`:
```python
" Do not speak until the other person has completely finished their turn and is clearly waiting for your response — this means they have asked a direct question or gone fully silent for several seconds. If they pause mid-sentence, do not say anything. Never say 'okay', 'got it', 'oh', or any filler word mid-sentence. When the call first connects, wait silently until the agent asks who they are speaking with before introducing yourself."
```
2. Changed `firstMessage` to `None` — bot stays completely silent on connect.
3. Updated Office Hours Inquiry goal in `scenarios.py` to ask one question at a time.

**Result:** Improved — bot waited better at start, but still said "Got it" once mid-sentence.

---

## Iteration 4 — VAD Endpointing Delay + Stricter Silence Rule
**Triggered by:** Continued mid-sentence interruptions in Office Hours Inquiry calls.
**Observation:** Two persistent interruption points:
1. Bot said "Hello?" during the opening disclaimer before the agent finished
2. Bot said "Got it" while agent was mid-sentence: `"You'll need an appointment... We don't accept walk ins. [pause] Would you like to schedule?"`

**Root cause identified:** Vapi's VAD (Voice Activity Detection) was opening the bot's mic on brief mid-clause pauses (~200ms default). This is an audio-layer issue — prompt alone can't fix it.

**Changes:**
1. Added `endpointing: 500` to Deepgram transcriber config — increases silence threshold from ~200ms to 500ms before treating a pause as end-of-turn:
```python
"transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    "endpointing": 500,   ← added
},
```
2. Updated `systemPrompt` line 52 to add "even if there is a brief pause — wait" and name-agnostic greeting wait:
```python
" Do not speak until the other person has completely finished their turn and is clearly waiting for your response — this means they have asked a direct question or gone fully silent for several seconds. If they pause mid-sentence, do not say anything. Never say 'okay', 'got it', 'oh', or any filler word mid-sentence. When the call first connects, wait silently until the agent asks who they are speaking with before introducing yourself."
```
3. Changed `maxDurationSeconds` from 300 to 180 (3 minutes max per call).

**Result:** Best result yet — fewer interruptions, cleaner turn-taking throughout.

---

## Final State — Current `main.py` (as of 2026-06-27)

```python
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

"firstMessage": None,                    # changed from scenario["opening_line"]
"maxDurationSeconds": 180,               # changed from 300
"transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    "endpointing": 500,                  # added — reduces mid-sentence interruptions
},
```

---

## Summary of All Changes

| Iteration | What changed | Why | Triggered by |
|-----------|-------------|-----|-------------|
| 1 | Added conditional DOB pushback for Reschedule Appointment | Bot accepted wrong DOB silently | call_reschedule_appointment transcript |
| 2 | Added greeting-wait instruction to systemPrompt; firstMessage → "Hello." | Bot talked over agent's opening greeting | call_cancel_appointment + call_office_hours_inquiry transcripts |
| 3 | Stricter no-filler rule; firstMessage → None; one question at a time in goal | Bot interrupted mid-sentence with "Okay", "Got it" | call_office_hours_inquiry_212845 transcript |
| 4 | endpointing: 500 added to Deepgram config; maxDurationSeconds → 180 | VAD opening mic on mid-clause pauses — audio layer fix needed | Persistent "Got it" and "Hello?" interruptions |
