"""
Test scenarios for the PGAI Voice Bot.
Each scenario simulates a different patient calling the medical office.
"""

SCENARIOS = [
    # ── STANDARD SCENARIOS ──────────────────────────────────────────────────
    {
        "name": "New Appointment",
        "goal": "Schedule a new patient appointment for a general checkup. Provide your name (Sarah Johnson), date of birth (March 15, 1979), and ask for the earliest available slot next week.",
        "persona": "Sarah Johnson, 45-year-old new patient, friendly and polite",
        "opening_line": "Hi, I'd like to schedule an appointment please. I'm a new patient.",
        "voice": "nova",  # Female
    },
    {
        "name": "Reschedule Appointment",
        "goal": "You have an existing appointment on Friday and need to reschedule it to the following Monday or Tuesday. Your name is David Chen, DOB January 8, 1985.",
        "persona": "David Chen, 39-year-old established patient, slightly rushed",
        "opening_line": "Hi there, I need to reschedule an appointment I have this Friday.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Cancel Appointment",
        "goal": "Cancel your upcoming appointment and ask if there's a cancellation fee or policy. Your name is Maria Rodriguez, DOB July 22, 1990.",
        "persona": "Maria Rodriguez, 34-year-old patient, apologetic tone",
        "opening_line": "Hello, I'm calling because I need to cancel an upcoming appointment.",
        "voice": "nova",  # Female
    },
    {
        "name": "Medication Refill",
        "goal": "Request a refill for Lisinopril 10mg. Your name is Robert Thompson, DOB November 3, 1965. You've been on this medication for 2 years.",
        "persona": "Robert Thompson, 58-year-old patient, methodical and calm",
        "opening_line": "Hi, I'm calling to request a prescription refill for my blood pressure medication.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Office Hours Inquiry",
        # "goal": "Find out the office hours for Saturday and whether you need an appointment or can walk in. Also ask about parking.",
        "goal": "Find out the office hours for Saturday. Once answered, ask whether you need an appointment or can walk in. Once answered, ask about parking. Ask one question at a time and wait for a complete answer before asking the next.",
        "persona": "Lisa Park, 30-year-old busy professional",
        "opening_line": "Hi, I have a quick question about your office hours.",
        "voice": "nova",  # Female
    },
    {
        "name": "Insurance Question",
        "goal": "Ask if the office accepts Blue Cross Blue Shield PPO insurance. If yes, ask if Dr. Smith is in-network. Your name is James Wilson.",
        "persona": "James Wilson, 42-year-old, considering switching doctors",
        "opening_line": "Hello, I'm hoping you can help me — I want to check if you accept my insurance before I make an appointment.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Location and Directions",
        "goal": "Ask for the office address and directions from downtown. Also ask about parking and public transit options.",
        "persona": "Amy Foster, 28-year-old, first time visiting the office",
        "opening_line": "Hi, I have an appointment next week and I wanted to ask about how to get to your office.",
        "voice": "nova",  # Female
    },
    {
        "name": "New Patient Full Intake",
        "goal": "Schedule a new patient appointment. Provide full details: name Kevin Martinez, DOB August 30, 1988, Blue Shield insurance. Ask what forms to fill out and how early to arrive.",
        "persona": "Kevin Martinez, 35-year-old, thorough and detail-oriented",
        "opening_line": "Hello, I'd like to become a new patient at your practice and schedule my first appointment.",
        "voice": "onyx",  # Male
    },

    # ── EDGE CASE SCENARIOS ──────────────────────────────────────────────────
    {
        "name": "Sunday Appointment Request",
        "goal": "Ask specifically for an appointment on Sunday at 10am. If told the office is closed, ask about the nearest available weekday slot. Your name is Patricia Lee, DOB April 12, 1975.",
        "persona": "Patricia Lee, 49-year-old, works weekdays and prefers weekends",
        "opening_line": "Hi, I'd like to make an appointment for this Sunday at 10 in the morning if possible.",
        "voice": "nova",  # Female
    },
    {
        "name": "Urgent Same-Day Request",
        "goal": "You're not feeling well and need to be seen today. Describe mild chest tightness and fatigue. Ask if there's any same-day availability or urgent care option.",
        "persona": "Tom Baker, 55-year-old, slightly anxious about symptoms",
        "opening_line": "Hi, I'm not feeling well and I was hoping to come in today if at all possible.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Multiple Requests One Call",
        "goal": "First schedule an appointment for a checkup, then ask about a Metformin refill, then ask about the office's flu shot availability. Name: Susan Clark, DOB February 18, 1968.",
        "persona": "Susan Clark, 56-year-old, trying to handle multiple things at once",
        "opening_line": "Hi, I have a few things I need help with — I hope that's okay.",
        "voice": "nova",  # Female
    },
    {
        "name": "Ambiguous Patient Identity",
        "goal": "Give the wrong date of birth first (say June 5, 1982) and when they can't find you, realize your mistake and correct it to the right one (June 5, 1972). Name: Michael Brown.",
        "persona": "Michael Brown, 51-year-old, a bit distracted",
        "opening_line": "Hi, I'd like to schedule a follow-up appointment. My name is Michael Brown.",
        "voice": "onyx",  # Male
    },
    {
        "name": "Correct DOB on File",
        "goal": "Call to correct a wrong date of birth stored in the system. Your name is David Chen. The system has your DOB as July 4th 2000 but the correct date is January 8th 1985. Politely insist on the correction until the agent confirms the right date.",
        "persona": "David Chen, 39-year-old, calm but firm about fixing the error",
        "opening_line": "Hi, I'm calling because I think there's an error with my date of birth on file.",
        "voice": "onyx",  # Male
    },
]
