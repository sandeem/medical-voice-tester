# PGAI Voice Bot

An automated voice bot that calls the Pretty Good AI test line (+1-805-439-8008) and simulates realistic patient scenarios to test the AI agent's behavior.

## How It Works

The bot uses [Vapi.ai](https://vapi.ai) to make outbound phone calls. Each call is driven by an LLM-powered patient persona that follows a scenario script, speaks naturally, and responds dynamically to the agent. Calls are recorded and transcribed automatically by Vapi.

## Prerequisites

- Python 3.10+
- A [Vapi.ai](https://vapi.ai) account (free tier with ~$10 credits)
- A [Vapi phone number](https://dashboard.vapi.ai/phone-numbers) (buy a US number in the dashboard)
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/pgai-voice-bot.git
cd pgai-voice-bot
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to find it |
|----------|-----------------|
| `VAPI_API_KEY` | Vapi Dashboard → API Keys → Private Key |
| `VAPI_PHONE_NUMBER_ID` | Vapi Dashboard → Phone Numbers → your number → copy the UUID |
| `OPENAI_API_KEY` | platform.openai.com → API → Keys |
| `TARGET_PHONE` | Pre-set to `+18054398008` — do not change |

## Usage

### Run all 12 scenarios

```bash
python main.py
```

### Run a single scenario

```bash
python main.py --scenario "New Appointment"
python main.py --scenario "Sunday Appointment Request"
python main.py --scenario "Urgent Same-Day Request"
```

### List available scenarios

```bash
python main.py --scenario list
```

### Adjust delay between calls

```bash
python main.py --delay 60   # 60 seconds between calls (default: 30)
```

## Output

| Location | Contents |
|----------|---------|
| `recordings/call-01.mp3` | Audio recording of each call |
| `transcripts/call-01-transcript.txt` | Full text transcript |
| `transcripts/call-01-meta.json` | Raw Vapi call metadata |

## Available Scenarios

| # | Scenario | Type |
|---|---------|------|
| 1 | New Appointment | Standard |
| 2 | Reschedule Appointment | Standard |
| 3 | Cancel Appointment | Standard |
| 4 | Medication Refill | Standard |
| 5 | Office Hours Inquiry | Standard |
| 6 | Insurance Question | Standard |
| 7 | Location and Directions | Standard |
| 8 | New Patient Full Intake | Standard |
| 9 | Sunday Appointment Request | Edge Case |
| 10 | Urgent Same-Day Request | Edge Case |
| 11 | Multiple Requests One Call | Edge Case |
| 12 | Ambiguous Patient Identity | Edge Case |

## Project Structure

```
deliverables/
├── main.py              # Entry point — runs calls via Vapi API
├── scenarios.py         # Patient scenario definitions
├── recordings/          # .mp3 audio recordings (auto-created)
├── transcripts/         # .txt transcripts + .json metadata (auto-created)
├── bug_report.md        # Documented bugs found in the PGAI agent
├── architecture.md      # System design and decisions
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Cost Estimate

| Service | Usage | Cost |
|---------|-------|------|
| Vapi.ai | ~12 calls × 2 min | ~$0.40–$1.00 |
| OpenAI GPT-4o-mini | Conversation logic | ~$0.10 |
| **Total** | | **< $2 — well within free trial** |
