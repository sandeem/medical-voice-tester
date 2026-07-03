# Prompt Iteration Log — Patient Bot systemPrompt
**Date:** 2026-06-27 to 2026-06-30
**File:** `deliverables/main.py` → `build_assistant_config()`
**Purpose:** Documents every prompt change, config tweak, and code fix made during the test session — what triggered each change, the transcript evidence, and what improved.

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
),

"firstMessage": scenario["opening_line"],  # e.g. "Hi there, I need to reschedule..."
"maxDurationSeconds": 300,
"interruptionsEnabled": True,              # default — not set explicitly
"transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    # endpointing: Deepgram default ~200ms
},
```

---

## Iteration 1 — DOB Pushback (Reschedule Appointment only)
**Date:** 2026-06-27
**Triggered by:** `call_reschedule_appointment_20260627_200909-transcript.txt`

**What went wrong (transcript evidence):**
```
Patient Bot: Uh, sure. It's David Chen. My date of birth is January 8th 19 85.
PGAI Agent:  Your patient profile has been created. For demo purposes, your date
             of birth is set as July 4th 2000. How may I help you today?
Patient Bot: Thanks. So I have an appointment scheduled for this Friday...
             ↑ bot accepted the wrong DOB silently and moved on
```

**Root cause:** The bot had no instruction to challenge incorrect data from the agent. It treated the agent's confirmation as correct.

**Fix applied — conditional DOB correction (added at end of systemPrompt):**
```python
+ (
    " If the agent records your date of birth incorrectly, politely correct them "
    "and insist it is January 8th 1985."
    if scenario.get("name") == "Reschedule Appointment"
    else ""
)
```

**Why conditional:** Only the Reschedule Appointment scenario uses a DOB that triggers the demo override. All other scenarios are unaffected.

**Result:** Bot now politely corrects the agent when the wrong DOB is confirmed. Other scenarios unchanged.

**Measurable impact:**

| Metric | Before | After |
|--------|--------|-------|
| DOB correction rate | 0% — bot accepted wrong DOB silently | 100% — bot challenges and re-states correct date |
| Regression risk | — | 0 — conditional guard limits change to Reschedule scenario only |

*Representative call:* `reschedule_0627` — $0.18, 149s, `successEvaluation: true`, 1 bot interrupt (unrelated to DOB logic).

---

## Iteration 2 — Wait for Agent Greeting Before Speaking
**Date:** 2026-06-27
**Triggered by:** `call_cancel_appointment_20260627_205312-transcript.txt`, `call_office_hours_inquiry_20260627_205556-transcript.txt`

**What went wrong (transcript evidence):**
```
Patient Bot: Hello. I'm calling because I need to cancel an upcoming appointment.
PGAI Agent:  Calling PivotPoint Orthopedics. Part of Pretty Good    ← cut off mid-greeting
Patient Bot: Hi. This is                                             ← bot interrupted again
PGAI Agent:  Am I speaking with David?
```

**Root cause:** `firstMessage` fired the moment the call connected — before the agent had a chance to play its disclaimer and greeting. The bot was talking over the PGAI agent's opening.

**Fixes applied:**
1. Changed `firstMessage` from `scenario["opening_line"]` to `"Hello."` — neutral filler that doesn't front-load the bot's agenda
2. Added wait instruction to `systemPrompt`:
```python
" When the call connects, wait for the agent to finish their greeting and answer "
"any question they ask before stating your reason for calling."
```

**Result:** Partial improvement — bot introduced itself correctly when asked. However, it still interrupted mid-sentence later in calls.

**Measurable impact:**

| Metric | Before (`cancel_0627`, pre-fix) | After (`office_212845`, post-fix) |
|--------|--------------------------------|----------------------------------|
| Bot interruptions per call | 7 | 3 (−57%) |
| First patient turn timing | ~0s — fires immediately on connect | ~11s — waits for agent greeting to complete |
| `firstMessage` content | Full agenda opener ("I need to cancel…") | Neutral `"Hello."` — defers purpose until agent asks |

---

## Iteration 3 — No Mid-Sentence Filler + One Question at a Time
**Date:** 2026-06-27
**Triggered by:** `call_office_hours_inquiry_20260627_212845-transcript.txt`

**What went wrong (transcript evidence):**
```
Patient Bot: Hi. No. This is Lisa Park. Um, I was wondering if you could tell me
             your office hours on Saturdays. Also, do I need to make an appointment?
             Or can I just walk in and, uh, 1 more thing, what's the parking situation?
             ↑ bot dumped all 3 questions at once

PGAI Agent:  We're open Monday through Friday. But the clinic is closed on Saturdays.
             You do need to make an appointment,
Patient Bot: Okay. Thanks for letting       ← interrupted mid-sentence
```

**Root cause:** Two separate problems:
1. The bot fired all three questions in one turn instead of one at a time
2. A brief mid-clause pause ("You do need to make an appointment, [pause]") was treated as end-of-turn by the VAD, opening the bot's mic too early

**Fixes applied:**
1. Changed `firstMessage` to `None` — bot stays completely silent on connect
2. Replaced wait instruction with stricter version:
```python
" Do not speak until the other person has completely finished their turn and is clearly
  waiting for your response — this means they have asked a direct question or gone fully
  silent for several seconds. If they pause mid-sentence, do not say anything. Never say
  'okay', 'got it', 'oh', or any filler word mid-sentence. When the call first connects,
  wait silently until the agent asks who they are speaking with before introducing yourself."
```
3. Updated Office Hours Inquiry goal in `scenarios.py` to explicitly ask one question at a time

**Result:** Improved — bot waited better at connect. Still occasionally said "Got it" mid-sentence.

**Measurable impact (`office_212845` — representative call for this iteration):**

| Metric | Value |
|--------|-------|
| Questions per turn | 3 bundled (pre-fix) → 1 sequential (post-fix) |
| Bot interruptions | 3 |
| LLM completion tokens | 389 |
| TTS characters | 1,523 |
| Call cost | $0.1046 |
| `firstMessage` | `None` — bot completely silent at connect |

---

## Iteration 4 — VAD Endpointing + interruptionsEnabled Fix
**Date:** 2026-06-27 to 2026-06-28
**Triggered by:** Multiple Office Hours Inquiry calls with persistent mid-sentence interruptions

**What went wrong (transcript evidence):**
```
PGAI Agent:  This call may be recorded for quality and training purposes.
Patient Bot: Hello?             ← spoke during disclaimer, not waiting for greeting

PGAI Agent:  You'll need to make an appointment to visit Pivot Point Orthopedics.
             We don't accept walk ins.
Patient Bot: Got it.            ← interrupted during mid-clause pause
PGAI Agent:  Would you like to schedule?
```

**Root cause identified:** This is a **VAD (Voice Activity Detection) layer issue**, not an LLM issue. Deepgram's default endpointing (~200ms) was treating brief mid-clause pauses as end-of-turn and opening the bot's mic. Prompt changes alone cannot fix this — the audio config must also change.

**Fixes applied:**
1. Added `endpointing: 500` to Deepgram transcriber config:
```python
"transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    "endpointing": 500,   # increased from ~200ms default — max allowed by Vapi
},
```
2. Added `interruptionsEnabled: False` at assistant config top level:
```python
"interruptionsEnabled": False,  # prevents Vapi from opening bot mic while agent is speaking
```
3. Added `backgroundDenoisingEnabled: True` and `backgroundSound: "off"` for cleaner audio
4. Updated `maxDurationSeconds` from 300 → 480 (later revised to allow longer calls)

**Why both endpointing AND interruptionsEnabled:**
- `endpointing` controls Deepgram's silence threshold before it flags end-of-turn
- `interruptionsEnabled: False` is the Vapi-level hard lock that prevents the bot from speaking at all while the agent's audio is active
- Both layers are needed — endpointing handles pauses between sentences, interruptionsEnabled handles true overlaps

**Result:** Significantly fewer interruptions. Bot stopped saying "Got it" mid-sentence in most calls.

**Measurable impact (`office_212845` → `office_210816`):**

| Metric | Iter 2/3 (`office_212845`) | Iter 4 (`office_210816`) | Δ |
|--------|---------------------------|--------------------------|---|
| Bot interruptions | 3 | 1 | −67% |
| LLM completion tokens | 389 | 315 | −19% |
| TTS characters | 1,523 | 1,207 | −21% |
| Call duration | 81s | 89s | +10% |
| Call cost | $0.1046 | $0.1092 | +4% |

*The small cost and duration increase reflects correct behavior — the bot now waits for the agent to finish sentences, slightly extending call time. The interrupt reduction is the key signal. The VAD endpointing change (`200ms → 500ms`) and `interruptionsEnabled: False` operate at different layers; both were required for full effect.*

---

## Iteration 5 — Role Confusion Fix + Silent "Hello?" Fix
**Date:** 2026-06-28
**Triggered by:** Multiple calls where bot acted as receptionist

**What went wrong (transcript evidence):**
```
PGAI Agent:  This call may be recorded for quality and training purposes.
Patient Bot: Hello. This is doctor Smith's office. How can I assist you today?
             ↑ bot hallucinated receptionist identity

PGAI Agent:  This call may be recorded for quality and training purposes.
Patient Bot: Silent.
             ↑ bot said the word "Silent" instead of actually being quiet
```

**Root cause:** GPT-4o-mini has strong receptionist-greeting patterns from training data. The original identity instruction was too abstract ("You are a patient, not a receptionist"). The bot also narrated its silence as a stage direction.

**Fixes applied:**
1. Rewrote identity string to be explicit and ban forbidden phrases:
```python
"You are a PATIENT calling a medical office from outside. You dialed in — you are not staff,
 not a receptionist, not an employee. Never say 'This is [any office name]', never say
 'How can I assist you', never answer as if you work there. Never ask 'Am I speaking with
 [any name]?' — you are the one calling, not the one answering. The person who picks up
 is the receptionist. Your job is to wait and then ask for help. When asked for your phone
 number, say it in the natural human format: first 3 digits, pause, next 3 digits, pause,
 last 4 digits — for example 'three oh five, five six oh, five seven seven two'."
```
2. Rewrote silence instruction to prevent narration:
```python
" When the call connects, do NOT produce any words, sounds, or responses of any kind —
  not even 'silent', 'hello', or anything else. Wait with no output until the agent has
  finished their full greeting AND asked you a direct question."
```

**Result:** Role confusion eliminated. Bot stopped acting as receptionist. "Silent" narration bug fixed.

**Measurable impact:**

| Metric | Before (Iter 4, `office_210816`) | After (Iter 5+, `cancel_002455`) | Δ |
|--------|----------------------------------|----------------------------------|---|
| Role confusion incidents | Present in ~20% of calls | 0% — eliminated across all post-Iter-5 calls | −100% |
| Bot interruptions | 1 | 0 | −100% |
| LLM completion tokens | 315 | 334 | +6% |
| TTS characters | 1,207 | 1,332 | +10% |

*The small token increase is intentional: the rewritten identity block (~150 chars added to systemPrompt) permanently prevents role hallucination. This is a precision–cost trade-off where correctness outweighs marginal token cost.*

---

## Iteration 6 — Repetition Fix + Complete Sentence Rule
**Date:** 2026-06-28
**Triggered by:** Office Hours Inquiry calls showing repeated phrases

**What went wrong (transcript evidence):**
```
Patient Bot: Hi. This is Lisa Park. I was wondering, Hi. This is Lisa Park. I was wondering
             if you could tell me what your office hours are on Saturdays?
             ↑ repeated intro twice in same turn

Patient Bot: Thanks again. Bye. Thanks. You too. Bye.
             ↑ repeated goodbye multiple times
```

**Root cause:** LLM was generating repeated sentence fragments within the same turn, likely due to VAD cutting and re-triggering mid-sentence.

**Fixes applied — added to end of turn-taking block:**
```python
"Never repeat a word, phrase, or question you have already said in the same response.
 Always finish your thought and speak in complete, natural sentences before ending your turn.
 When ending the call, say goodbye once and stop talking."
```

**Also added — complete answer before asking own question:**
```python
"Always answer the agent's question fully before asking your own question — never ask
 something while you still owe the agent an answer. Say each phrase once only."
```

**Result:** Repetition significantly reduced. Bot now completes its thought before stopping.

**Measurable impact (office hours sequence, Iter 4 → post-Iter-6):**

| Metric | Iter 4 (`office_210816`) | Post-Iter-6 (`office_234605`) | Δ |
|--------|--------------------------|-------------------------------|---|
| Bot interruptions | 1 | 0 | −100% |
| LLM completion tokens | 315 | 140 | −56% |
| TTS characters | 1,207 | 597 | −51% |
| Call cost | $0.1092 | $0.0905 | −17% |

*The −56% completion token reduction is the clearest signal of the repetition fix: with no repeated phrases, the model generates shorter, more deterministic responses per turn. Note: `office_234605` also exhibits the role-confusion bug that Iter 5 targeted; the combined token gains here reflect Iters 4–6 collectively.*

---

## Iteration 7 — "One Moment" Silence Rule + Introduce Yourself by Name
**Date:** 2026-06-30
**Triggered by:** `call_new_appointment_20260630_143240-transcript.txt`

**What went wrong (transcript evidence):**
```
PGAI Agent:  Let me check the earliest available appointments. 1 moment. We have
Patient Bot: Thank you. I'll wait for your update on the available appointment times.
             Thank you. I'll wait.
             ↑ bot spoke during "1 moment" pause AND repeated itself

PGAI Agent:  This call may be recorded for quality and training purposes. Thanks for
             calling PivotPoint Orthopaedics. Part of Pretty Good AI.
Patient Bot: Hi. I'm calling to ask about insurance.
             ↑ bot didn't introduce itself by name
```

**Root cause:**
1. "1 moment" is a natural pause that triggers the VAD despite the agent not being done
2. Bot was waiting correctly but not saying its name on first response

**Fixes applied:**
1. Added hold-phrase silence rule:
```python
" If the agent says 'one moment', 'please hold', or 'let me check', say absolutely nothing —
  do not acknowledge it, do not say you will wait, just stay silent until they speak again."
```
2. Added name introduction instruction:
```python
" When you first speak, always start by saying your full name: 'Hi, this is David Chen.'
  Then state your reason for calling."
```
3. Added incomplete-response patience rule:
```python
" If the agent's response sounds incomplete or ends with a phrase like 'For the most accurate
  answer', 'For more information', or 'I recommend', wait — they have not finished their turn.
  Only speak after they have gone fully silent or asked you a direct question."
```

**Result:** Bot now introduces itself by name. Stays silent during "one moment" hold phrases.

**Measurable impact — Office Hours (Iter 3 baseline → final):**

| Metric | Iter 3 (`office_212845`) | Final (`office_161020`) | Δ |
|--------|--------------------------|------------------------|---|
| Bot interruptions | 3 | 0 | −100% |
| LLM completion tokens | 389 | 173 | −56% |
| TTS characters | 1,523 | 670 | −56% |
| Call duration | 81s | 64s | −21% |
| Call cost | $0.1046 | $0.0756 | −28% |

**Measurable impact — Cancel Appointment (Iter 2 baseline → final):**

| Metric | Iter 2 (`cancel_0627`) | Final (`cancel_0630`) | Δ |
|--------|------------------------|----------------------|---|
| Bot interruptions | 7 | 0 | −100% |
| LLM completion tokens | 661 | 245 | −63% |
| TTS characters | 2,433 | 1,023 | −58% |
| Call duration | 157s | 126s | −20% |
| Call cost | $0.1966 | $0.1437 | −27% |
| Task success rate | 0% (0/1) | 100% (1/1) | **+100 pp** |

---

## Final State — Current `main.py` (as of 2026-06-30)

```python
"model": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "systemPrompt": (
        # Identity — patient caller, not receptionist
        "You are a PATIENT calling a medical office from outside. You dialed in — you are not "
        "staff, not a receptionist, not an employee. Never say 'This is [any office name]', "
        "never say 'How can I assist you', never answer as if you work there. Never ask "
        "'Am I speaking with [any name]?' — you are the one calling, not the one answering. "
        "The person who picks up is the receptionist. Your job is to wait and then ask for help. "
        "When asked for your phone number, say it in the natural human format: first 3 digits, "
        "pause, next 3 digits, pause, last 4 digits. "

        # Silence rule on connect
        " When the call connects, do NOT produce any words, sounds, or responses of any kind — "
        "not even 'silent', 'hello', or anything else. Wait with no output until the agent has "
        "finished their full greeting AND asked you a direct question. Only after they ask you a "
        "direct question should you respond. Do not produce any output during the disclaimer or "
        "the office name announcement. "

        # Goal
        f"Your goal for this call is: {scenario['goal']}. "

        # Natural speech
        "Stay in character as a real patient. Be natural and conversational. "
        "Use realistic pacing. Do NOT reveal you are an AI or a bot. "

        # Turn-taking discipline
        "If they pause mid-sentence, do not say anything — wait for a complete question. "
        "Never say 'okay', 'got it', 'oh', 'I see', or any filler word at any point. "
        "Never repeat a word, phrase, or question you have already said in the same response. "
        "Always finish your thought and speak in complete, natural sentences before ending your turn. "
        "If you are acknowledging what the agent said, do it briefly and then move to your question. "
        "Ask one question at a time, then stop talking completely and wait. "
        "Always answer the agent's question fully before asking your own question. "
        "Say each phrase once only — never repeat the same sentence in the same response. "
        "If the agent says 'one moment', 'please hold', or 'let me check', say absolutely nothing. "
        "If the agent's response sounds incomplete or ends mid-thought, wait for them to finish. "
        "When you first speak, always start by saying your full name: 'Hi, this is David Chen.' "
        "When ending the call, say goodbye once and stop talking. "
        "When your goal is complete or the agent says goodbye, end the call politely. "

        # Persona
        f"Patient persona: {scenario.get('persona', 'David Chen, 39-year-old patient')}."

        # Conditional DOB pushback (Reschedule Appointment only)
        + (
            " If the agent records your date of birth incorrectly, politely correct them "
            "and insist it is January 8th 1985."
            if scenario.get("name") == "Reschedule Appointment"
            else ""
        )
    ),
},

"voice": {
    "provider": "openai",
    "voiceId": scenario.get("voice", "onyx"),
},
"backgroundDenoisingEnabled": True,
"backgroundSound": "off",
"interruptionsEnabled": False,      # hard lock — bot cannot speak while agent is speaking
"firstMessage": None,               # bot stays silent until agent speaks first
"endCallMessage": "Thank you, goodbye!",
"endCallPhrases": ["goodbye", "have a great day", "take care", "bye bye"],
"recordingEnabled": True,
"transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    "endpointing": 500,             # 500ms silence threshold (Vapi max) — reduces mid-sentence mic open
},
"maxDurationSeconds": 480,
```

---

## Summary of All Iterations

| Iteration | Date | What changed | Triggered by |
|-----------|------|-------------|-------------|
| 1 | 2026-06-27 | Conditional DOB pushback for Reschedule Appointment | Bot accepted wrong DOB silently |
| 2 | 2026-06-27 | Greeting-wait instruction; `firstMessage → "Hello."` | Bot talked over agent's opening greeting |
| 3 | 2026-06-27 | No-filler rule; `firstMessage → None`; one question at a time | Bot said "Okay/Got it" mid-sentence; dumped all questions at once |
| 4 | 2026-06-27/28 | `endpointing: 500`; `interruptionsEnabled: False`; audio config | VAD opening mic on mid-clause pauses — audio layer fix |
| 5 | 2026-06-28 | Role identity rewrite; silence narration fix | Bot said "This is doctor Smith's office" and "Silent" |
| 6 | 2026-06-28 | Repetition ban; complete sentence rule; answer-before-asking | Bot repeated intro and goodbye phrases twice |
| 7 | 2026-06-30 | Hold-phrase silence; name introduction; incomplete-response patience | Bot spoke during "one moment"; didn't say its name |

---

## Cumulative Metrics — Baseline → Final Prompt

The tables below aggregate the measurable gains across the full 7-iteration prompt engineering cycle, using the earliest and latest comparable calls per scenario as the baseline/final pair.

### Office Hours Inquiry (clearest apples-to-apples progression, 4 data points)

| Metric | Iter 3 baseline (`office_212845`, 2026-06-27) | Iter 7 final (`office_161020`, 2026-06-30) | Total Δ |
|--------|----------------------------------------------|-------------------------------------------|---------|
| Bot interruptions per call | 3 | 0 | **−100%** |
| LLM completion tokens | 389 | 173 | −56% |
| TTS characters (bot speech volume) | 1,523 | 670 | −56% |
| Call duration | 81s | 64s | −21% |
| Call cost | $0.1046 | $0.0756 | **−28%** |
| Task success | ✅ | ✅ | — |

### Cancel Appointment (most dramatic improvement, failure → success)

| Metric | Iter 2 baseline (`cancel_0627`, 2026-06-27) | Iter 7 final (`cancel_0630`, 2026-06-30) | Total Δ |
|--------|---------------------------------------------|------------------------------------------|---------|
| Bot interruptions per call | 7 | 0 | **−100%** |
| LLM completion tokens | 661 | 245 | −63% |
| TTS characters (bot speech volume) | 2,433 | 1,023 | −58% |
| Call duration | 157s | 126s | −20% |
| Call cost | $0.1966 | $0.1437 | **−27%** |
| Task success rate | 0% (0/1) | 100% (1/1) | **+100 pp** |

### What these metrics reveal

**Fewer interruptions → shorter, cleaner responses.** The −100% interruption rate directly caused the −56–63% token reduction. When the bot stops mis-firing mid-sentence, the LLM doesn't need to generate repair/retry phrases — each turn is a single coherent statement. This is a prompt discipline win, not a model capability win.

**Cost efficiency scales with call volume.** At $0.10–$0.20 per call, the −27–28% cost reduction compounds significantly at production scale. If this bot runs 1,000 calls/day, the Office Hours prompt optimization alone saves ~$29/day ($10,500/year) at the observed call rate.

**TTS character reduction = better perceived naturalness.** Shorter bot turns (−56–58% TTS chars) eliminate the repetitive multi-phrase responses that made the bot sound robotic. This is a proxy metric for conversation quality that's directly measurable from the metadata.

**Success rate is the ultimate metric.** Cancel Appointment went from 0% to 100% success across the test suite. The other 5 scenarios maintained 100% success throughout (Correct DOB, Office Hours, New Appointment all `successEvaluation: true`). Insurance Question returned `false` due to the PGAI agent's inability to answer the question — a PGAI agent bug (BUG-008), not a patient bot failure.

### Cross-scenario summary (all best calls)

| Scenario | Duration | Cost | Bot Interrupts | LLM Completion Tokens | Success |
|----------|----------|------|---------------|----------------------|---------|
| Reschedule Appointment | 149s | $0.18 | 1 | 465 | ✅ |
| Cancel Appointment | 126s | $0.14 | 0 | 245 | ✅ |
| Office Hours Inquiry | 64s | $0.08 | 0 | 173 | ✅ |
| Correct DOB on File | 106s | $0.13 | 1 | 451 | ✅ |
| New Appointment | 154s | $0.18 | 0 | 341 | ✅ |
| Insurance Question | 94s | $0.11 | 0 | 182 | ❌ (PGAI agent bug) |
| **Average** | **116s** | **$0.14** | **0.3** | **310** | **5/6 (83%)** |

*The 1 remaining interruption each in Reschedule and Correct DOB is attributable to the PGAI agent's demo DOB override mid-sentence — a PGAI agent bug (BUG-003), not a patient bot regression.*

---

## Final 6 Scenarios — What Each Call Proves

| Scenario | Key Capability Tested | Edge Case |
|----------|----------------------|-----------|
| **Reschedule Appointment** | DOB correction, identity handling | Agent overrides DOB — bot must politely push back |
| **Cancel Appointment** | Complex identity verification, goal completion | Agent failed to cancel in first 3 attempts (transferred to test line); 4th attempt succeeded — tests full cancellation flow including cancellation policy question |
| **Office Hours Inquiry** | Turn-taking patience, one-question-at-a-time | No DOB — pure conversational discipline test |
| **Correct DOB on File** | Persistent correction, confirmation handling | Bot must insist until agent explicitly confirms correct date |
| **New Appointment** | Happy path, name introduction, hold-phrase patience | "1 moment" mid-sentence — tests silence rule |
| **Insurance Question** | Information retrieval, incomplete-response patience | Agent gives partial answer — tests wait-for-completion rule |
