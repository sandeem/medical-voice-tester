# Bug Report — PGAI Agent Testing

**Test Date:** June 27–30, 2026  
**Calls Made:** 24  
**Test Number:** +1-805-439-8008  
**System Under Test:** Pivot Point Orthopedics AI Agent (Pretty Good AI)

---

## BUG-001

**Severity:** High  
**Call:** All calls (observed in every scenario tested)  
**Timestamp:** First agent turn (~7–11 seconds into call)  
**Scenario:** All scenarios (Office Hours, Cancel Appointment, Reschedule, Correct DOB)

**Description:**  
The agent's opening greeting always asks "Am I speaking with David?" regardless of who is actually calling. Every single call tested — whether from Maria Rodriguez, Lisa Park, or even a third-party clinic receptionist — triggers this hardcoded name check. The name "David" appears to be a default or leftover test value baked into the agent's greeting prompt.

**Expected behavior:**  
The agent should greet callers with a neutral, name-agnostic opening (e.g., "How can I help you today?") or, if caller ID data is available, use it correctly. It should not address an unknown caller by a specific first name.

**Actual behavior:**  
Agent says "Am I speaking with David?" on the very first turn of every call. Callers must immediately correct the agent before proceeding. Observed verbatim in 18 out of 20 calls.

**Impact:**  
Every call starts with the patient correcting a wrong name. This is jarring, unprofessional, and erodes caller trust before the actual request is even stated. Callers who have the same name by coincidence would not catch the error, potentially causing a data mix-up.

---

## BUG-002

**Severity:** Critical  
**Call:** `call_cancel_appointment_20260627_205312`, `call_cancel_appointment_20260629_002455`, `call_cancel_appointment_20260629_003458`  
**Timestamp:** Late in call (~120–150 seconds) after full identity verification  
**Scenario:** Cancel Appointment

**Description:**  
The agent successfully collects patient identity (name, DOB, phone number) across a multi-step verification flow, but then fails to perform the actual cancellation. It responds with "I can't access the appointment details right now" and transfers the caller — which drops to a recorded test line message and ends the call. The caller's secondary question about the cancellation fee or policy is also never addressed in any of the three attempts. All three cancel calls are marked `successEvaluation: false` in the VAPI metadata.

**Expected behavior:**  
After verifying identity, the agent should retrieve the patient's upcoming appointment, confirm the details with the caller, process the cancellation, and answer whether a cancellation fee applies.

**Actual behavior:**  
Agent collects full identity, then says it cannot access appointment details and escalates to a representative. The transfer plays a "Pretty Good AI test line. Goodbye." recording and hangs up. Zero successful cancellations across 3 attempts. The cancellation policy question is ignored in all three calls.

**Impact:**  
The cancel appointment feature is completely non-functional. Patients who need to cancel cannot do so via the agent and get disconnected after a lengthy identity verification. This is the most critical failure in the test suite.

---

## BUG-003

**Severity:** High  
**Call:** `call_reschedule_appointment_20260627_200909`, `call_new_appointment_20260630_143240`  
**Timestamp:** ~9–27 seconds  
**Scenario:** Reschedule Appointment, New Appointment

**Description:**  
Two distinct demo/test artifacts surfaced in a live call. First, the agent asked "Would you like to create a demo patient profile?" — language that belongs in a sandbox environment, not in patient-facing calls. Second, after the caller gave their real DOB (January 8, 1985), the agent confirmed the profile was created but stated "For demo purposes, your date of birth is set as July 4th 2000." This hardcoded demo DOB overrides the patient's actual date of birth without informing them it is wrong. Notably, July 4th 2000 is the same incorrect DOB found in the "Correct DOB" test scenario, confirming it is a shared demo data artifact.

Additionally, the agent told the caller it found no upcoming appointments, even though the caller explicitly said they had one on Friday. The agent offered to book a new appointment instead of investigating the discrepancy.

**Expected behavior:**  
The agent should use the caller's stated identity to look up their real record. Demo-specific language and hardcoded DOB overrides must not appear in any patient-facing call flow. If a stated appointment is not found, the agent should acknowledge the discrepancy and offer to connect the caller to a staff member.

**Actual behavior:**  
Agent exposed internal demo language, silently replaced the patient's real DOB with a test value, and failed to find the existing appointment — leading the patient to book a brand-new appointment instead of rescheduling.

**Impact:**  
Exposes test infrastructure details to callers. A real patient's record could be associated with a wrong DOB without their knowledge. The reschedule task was not completed as intended — the patient ended the call having booked a new appointment while still believing their Friday appointment exists.

---

## BUG-004

**Severity:** Medium  
**Call:** `call_cancel_appointment_20260627_205312`, `call_correct_dob_on_file_20260627_202958`, `call_office_hours_inquiry_20260627_220443`, `call_office_hours_inquiry_20260628_210816`  
**Timestamp:** Varies per call (multiple turns)  
**Scenario:** All scenarios

**Description:**  
The agent's spoken responses are cut off mid-sentence in multiple calls. Examples observed:

- `cancel_20260627_205312`: *"Calling PivotPoint Orthopedics. Part of Pretty Good"* — greeting truncated before identifying as an AI agent.
- `correct_dob_20260627_202958`: *"I can't update your date of birth directly. But I can let our clinic support team know about the"* — explanation ends without completing the thought.
- `office_hours_20260627_220443`: *"Walk ins aren't guaranteed a spot since our providers"* — policy explanation stops mid-sentence.
- `office_hours_20260628_210816`: *"Yes. There is free patient parking available in the surface"* — answer about parking is incomplete.

The likely cause is overly aggressive voice activity detection (VAD) or endpointing settings that allow the patient-side audio to interrupt the agent before it finishes speaking.

**Expected behavior:**  
The agent should complete each spoken response fully before yielding the turn to the caller.

**Actual behavior:**  
Responses are cut off mid-sentence when the caller begins speaking or when there is a brief pause, leaving the caller with incomplete information.

**Impact:**  
Callers receive partial answers and may not understand what the agent said. In the cancel appointment call, even the opening greeting was cut off, creating a confusing first impression.

---

## BUG-005

**Severity:** Medium  
**Call:** `call_office_hours_inquiry_20260628_210816`, `call_office_hours_inquiry_20260628_234605`, `call_cancel_appointment_20260629_003458`  
**Timestamp:** Varies  
**Scenario:** Office Hours Inquiry, Cancel Appointment

**Description:**  
The agent produced garbled or factually incorrect text in several turns, including the clinic's own name:

- `office_hours_20260628_210816`: Agent says *"Hi, Lisa. **To the point** Orthopaedics is open Monday through Friday"* — clinic name corrupted ("To the point" instead of "Pivot Point").
- `office_hours_20260628_234605`: Agent says *"**Visit Point** Orthopedics. Is open Monday through Friday"* — clinic name corrupted again.
- `cancel_20260629_003458`: Agent says *"Please provide **Maria Rendering** as **his** date of birth"* — patient's name garbled into "Maria Rendering," and wrong pronoun ("his") used for a female patient.

These errors appear to originate from TTS-to-STT feedback loops or from the LLM generating hallucinated text rather than faithfully using the correct proper nouns.

**Expected behavior:**  
The agent should accurately reproduce the clinic name "Pivot Point Orthopedics" and use the patient's name and correct pronouns as provided.

**Actual behavior:**  
The clinic name is rendered incorrectly in at least 2 calls. In the cancel call, the patient's name is garbled and the wrong gender pronoun is used, which could cause identity confusion during a sensitive medical interaction.

**Impact:**  
An agent that mispronounces or misspells its own clinic name undermines credibility. Using a wrong pronoun for a patient is a compliance and patient-experience risk, particularly in a healthcare context.

---

## BUG-007

**Severity:** Low  
**Call:** `call_office_hours_inquiry_20260630_161020-transcript.txt`  
**Timestamp:** ~15 seconds  
**Scenario:** Office Hours Inquiry

**Description:**  
After the agent's opening greeting, the patient bot responded correctly but then repeated the question back to itself before asking it:
```
PGAI Agent: Am I speaking with David?
Patient Bot: Yes. That's me. We are your office hours for Saturday?
                              ↑ garbled repetition — "We are" instead of "What are"
```
The STT transcribed the bot's response as "We are your office hours for Saturday?" — a garbled version of "What are your office hours for Saturday?". This is a Deepgram STT artifact where the bot's first word ("What") was misheard as "We" and the question prefix was dropped, making the utterance grammatically incorrect but still contextually understandable to the agent.

**Expected behavior:**  
Bot should ask "What are your office hours on Saturday?" clearly and in a single, complete utterance.

**Actual behavior:**  
STT rendered "What are" as "We are", producing a garbled question that the agent nonetheless correctly interpreted.

**Impact:**  
Low severity — the agent understood the intent and answered correctly. However, this reveals that fast-speaking or clipped utterances from the bot can produce STT transcription errors that could mislead in more ambiguous contexts.

---

## BUG-008

**Severity:** Medium  
**Call:** `call_cancel_appointment_20260630_161713-transcript.txt`  
**Timestamp:** ~90 seconds  
**Scenario:** Cancel Appointment

**Description:**  
The agent successfully cancelled the appointment but could not provide any information about the cancellation fee or policy — a key part of the patient's request:
```
PGAI Agent: I do not have information about cancellation fees or specific policies.
            Would you still like to proceed with canceling your appointment...
```
The agent acknowledged it lacked the information but still proceeded with the cancellation. The patient's secondary question ("Is there a cancellation fee?") was never answered across all 4 Cancel Appointment call attempts.

Additionally, the agent garbled the doctor's name across multiple turns in the same call — referring to the same doctor as "the big new Lacoste MD", "the big new Lukoski MD", and "z big new Lukaszky" within a single conversation, creating a confusing and unprofessional experience.

**Expected behavior:**  
The agent should either provide cancellation policy details or clearly state where the patient can find this information (e.g., "Please check your appointment confirmation email"). Doctor names should be consistent and correctly pronounced across turns.

**Actual behavior:**  
Cancellation policy question is deflected with no alternative. Same doctor's name is rendered differently across turns in the same call due to STT/TTS inconsistency.

**Impact:**  
Patients cannot get cancellation fee information via the agent. Inconsistent name rendering erodes trust in the system's reliability and accuracy.

---

## BUG-006

**Severity:** Medium  
**Call:** `call_new_appointment_20260630_143240`  
**Timestamp:** ~60–90 seconds  
**Scenario:** New Appointment

**Description:**  
While the patient was providing their date of birth, the agent played a brief "one moment" or hold cue mid-sentence (*"Let me check the earliest available appointments for a new patient checkup next week. 1 moment. We have..."*). The agent resumed speaking before completing the sentence, cutting off the available slot information. The caller received only a partial list of available times ("and 3 45 PM") with no context for which day those slots belonged to initially.

Additionally, the agent accepted the patient's DOB even though it was spoken with an STT stutter ("January 8 19 19 85" instead of "January 8 1985") and responded: *"The birthday doesn't match our records, but for demo purposes, I'll accept it."* This demo-acceptance language leaks internal testing behavior into patient-facing responses.

**Expected behavior:**  
The agent should complete its sentence before yielding the turn. When reading available appointment slots, it should provide the full context (day and time) in a single uninterrupted turn. DOB validation responses should not expose demo/test language to callers.

**Actual behavior:**  
Agent interrupted its own appointment list mid-sentence. Available times were presented without the corresponding day context. Demo fallback language ("for demo purposes, I'll accept it") was spoken aloud to the patient.

**Impact:**  
Patients receive incomplete scheduling information and must ask follow-up questions to clarify what was already being said. Demo language erodes trust and professionalism in a healthcare context.

---

## Summary

| ID | Severity | Scenario | Issue |
|----|----------|----------|-------|
| BUG-001 | High | All | Agent greets every caller as "David" — hardcoded name in greeting |
| BUG-002 | Critical | Cancel Appointment | Agent cannot access appointment data; cancellation fails 3/3 times; cancellation policy never answered |
| BUG-003 | High | Reschedule Appointment, New Appointment | Demo mode artifacts ("create a demo patient profile," DOB overridden to July 4, 2000) exposed in live call |
| BUG-004 | Medium | All | Agent responses cut off mid-sentence due to aggressive VAD/endpointing |
| BUG-005 | Medium | Office Hours, Cancel | Clinic name garbled ("To the point," "Visit Point"); patient name garbled; wrong pronoun used |
| BUG-006 | Medium | New Appointment | Agent cuts off own appointment list mid-sentence; demo DOB acceptance language exposed to caller |
| BUG-007 | Low | Office Hours Inquiry | STT garbles bot's question ("We are your office hours" instead of "What are your office hours") |
| BUG-008 | Medium | Cancel Appointment | Agent cannot provide cancellation policy; doctor name rendered inconsistently across turns |
