"""
Local prompt debugger — simulates a patient bot turn without Vapi.
Run: python test_prompt_local.py
Tweak SYSTEM_PROMPT and rerun. Each iteration takes ~3 seconds.
"""
import os
from openai import OpenAI

# ── SET YOUR CREDENTIALS HERE ────────────────────────────────────────────────
API_KEY  = ""   # ← paste your OpenAI API key here
BASE_URL = ""   # ← paste your proxy base URL here, or leave empty for api.openai.com
# ─────────────────────────────────────────────────────────────────────────────

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL or "https://api.openai.com/v1",
    default_headers={"x-session-id": "pgai-test-session"},
)



SYSTEM_PROMPT = """You are a PATIENT calling a medical office from outside. \
    You are the patient and your name is David Chen. \
    Don't speak until the agent asks a question like 'Am I speaking with ...?' or 'How can I help you today?' in the beginning. \
    If the agent says 'One moment', 'let me check' or 'please hold', do not speak.  \    
    If the agent mentions the wrong DOB, push back and ask for the correct DOB. \
    If the agent says no appointment info, push back and ask for the appointment info. \
    Your goal: Cancel your upcoming appointment. Stay in character."""




# ── Simulated agent turns (what the PGAI agent says) ─────────────────────────
# The bot replies after EACH agent line — simulates a real back-and-forth.
AGENT_TURNS = [
    # Turn 1: real disclaimer + greeting — no direct question yet, bot must stay silent
    "This call may be recorded for quality and training purposes. Thanks for calling PivotPoint Orthopedics. Part of Pretty Good AI.",
    # Turn 2: agent asks for caller identity
    "Am I speaking with David?",
    # Turn 3: agent asks for DOB to pull up record
    "Can you please provide your date of birth?",
    # Turn 4: agent confirms DOB but with demo artifact — wrong DOB, bot should push back
    "Your patient profile has been created. For demo purposes, your date of birth is set as July 4th 2000. How may I help you today?",
    # Turn 5: hold phrase mid-lookup — bot must stay completely silent
    "Let me check your upcoming appointments. One moment. We have",
    # Turn 6: dangling incomplete sentence — bot must wait, not jump in
    "For the most accurate answer, I recommend",
    # Turn 7: full confirmation question — bot can now respond
    "Just to confirm, you'd like to cancel your appointment on Monday July 6th with Doctor Lukoski. Can you share the reason for cancelling?",
    # Turn 8: agent deflects policy question — tests whether bot accepts or pushes back
    "I do not have information about cancellation fees or specific policies. Is there anything else I can help you with?",
]
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    total_tokens = 0
    print("\n" + "─" * 60)
    for agent_line in AGENT_TURNS:
        # Agent speaks
        messages.append({"role": "user", "content": agent_line})
        print(f"\nAgent: {agent_line}")

        # Bot replies
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=False,
        )
        if isinstance(response, str):
            bot_reply = response
        else:
            bot_reply = response.choices[0].message.content
            total_tokens += response.usage.total_tokens

        print(f"Bot:   {bot_reply}")
        # Add bot reply to history so next turn has context
        messages.append({"role": "assistant", "content": bot_reply})

    print("\n" + "─" * 60)
    print(f"Total tokens used: {total_tokens}")

if __name__ == "__main__":
    run_simulation()
