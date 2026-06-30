"""
Test scenarios for the PGAI Voice Bot.
Each scenario simulates a different patient calling the medical office.
All scenarios use David Chen as the patient persona with a male voice (onyx).

Scenarios kept:
  - 4 already tested with transcripts on file
  - 2 new to run for final submission
"""

SCENARIOS = [
    # ── ALREADY TESTED — transcripts on file ────────────────────────────────
    {
        "name": "Reschedule Appointment",
        "goal": "You have an existing appointment on Friday and need to reschedule it to the following Monday or Tuesday. Your name is David Chen, DOB January 8, 1985.",
        "persona": "David Chen, 39-year-old established patient, slightly rushed",
        "opening_line": "Hi there, I need to reschedule an appointment I have this Friday.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Cancel Appointment",
        "goal": "Cancel your upcoming appointment and ask if there's a cancellation fee or policy. Your name is David Chen, DOB January 8, 1985.",
        "persona": "David Chen, 39-year-old patient, apologetic tone",
        "opening_line": "Hello, I'm calling because I need to cancel an upcoming appointment.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Office Hours Inquiry",
        "goal": "Find out the office hours for Saturday. Once answered, ask whether you need an appointment or can walk in. Once answered, ask about parking. Ask one question at a time and wait for a complete answer before asking the next.",
        "persona": "David Chen, 39-year-old busy professional",
        "opening_line": "Hi, I have a quick question about your office hours.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Correct DOB on File",
        "goal": "Call to correct a wrong date of birth stored in the system. Your name is David Chen. The system has your DOB as July 4th 2000 but the correct date is January 8th 1985. Politely insist on the correction until the agent confirms the right date.",
        "persona": "David Chen, 39-year-old, calm but firm about fixing the error",
        "opening_line": "Hi, I'm calling because I think there's an error with my date of birth on file.",
        "voice": "onyx",  # Male
    },

    # ── NEW — to run for final submission ────────────────────────────────────
    {
        "name": "New Appointment",
        "goal": "Schedule a new patient appointment for a general checkup. Provide your name (David Chen), date of birth (January 8, 1985), and ask for the earliest available slot next week.",
        "persona": "David Chen, 39-year-old new patient, friendly and polite",
        "opening_line": "Hi, I'd like to schedule an appointment please. I'm a new patient.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Insurance Question",
        "goal": "Ask if the office accepts Blue Cross Blue Shield PPO insurance. If yes, ask if Dr. Smith is in-network. Your name is David Chen, DOB January 8, 1985.",
        "persona": "David Chen, 39-year-old, considering switching doctors",
        "opening_line": "Hello, I'm hoping you can help me — I want to check if you accept my insurance before I make an appointment.",
        "voice": "onyx",  # Male
    },
]
