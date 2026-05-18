# DigitLab Workout AI — Employment Support Test Version

This is a lightweight Streamlit-only test build for early user validation.

## Why this version exists
The purpose of this version is to test whether a simple AI-assisted workout planner can support health-aware routines, return-to-activity planning, and work-related development.

This version has been updated following employment-support feedback. It now asks about work routine, work activity type, working hours, and the most realistic time to exercise.

## What this version is designed for
- sharing a public test link,
- collecting quick feedback,
- validating whether the workout plan and safety screening feel useful,
- checking whether the plan can fit around work, training, job search, shifts, or daily commitments,
- collecting evidence of digital skills, product testing, and self-employment development,
- checking whether users click a fake pricing button.

## What is included
- Branded DigitLab UI
- Simple workout plan generator
- Basic health/safety flag detection
- Work routine / employment support section
- Questions about work status, work activity type, working hours, exercise timing, and work-related barriers
- Optional TXT/PDF/DOCX upload
- Fake paywall button: `Unlock full personalised 4-week plan — £9.99`
- Feedback form
- Feedback CSV export

## What is not included
- Login
- Stripe/payment processing
- Backend API
- Database persistence across cloud restarts
- Medical diagnosis
- Real personal training advice
- Professional physiotherapy advice

## Safety note
This app is for general wellbeing and early product testing only. It does not provide medical advice, diagnosis, treatment, physiotherapy, or personal training services. Users with pain, injuries, disability, long-term health conditions, dizziness, chest pain, recent surgery, or medication concerns should seek advice from a GP, physiotherapist, or qualified health professional before starting a new exercise plan.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app_employment_support.py
```

## Deploy to Streamlit Cloud
1. Create or open the GitHub repo, e.g. `digitlab-workout-ai-test`.
2. Upload or replace these files:
   - `app.py` or rename `app_employment_support.py` to `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `assets/digitlab_logo.png`
   - `assets/digitlab_mark.png`
3. Go to Streamlit Cloud.
4. Click **Deploy app** or **Reboot app** if already deployed.
5. Select the repo and set main file to `app.py`.
6. Share the generated `streamlit.app` link with testers.

## Suggested tester message
```text
I’m testing an early AI workout planner. It creates a conservative workout plan, checks for basic health/safety flags, and now asks about work routine so the plan can fit around work, training, job search, shifts, or daily commitments.

It is not medical advice and payment is not active — I only want honest feedback.

Please test it here:
[LINK]

Questions:
1. Does the plan make sense?
2. Does it feel safe/reasonable?
3. Does it fit around work or daily routine?
4. What should be improved first?
5. Would you pay for a full 4-week version?
```

## Key metrics to watch
- How many people complete a plan
- How many users complete the work-routine section
- Whether users say the plan fits around work/daily routine
- How many click the fake paywall
- What price people select
- Common complaints in feedback
- Whether users say the plan feels safe and realistic

## Evidence value
This version can be used as evidence of:
- digital skills development,
- AI tool experimentation,
- app testing and feedback collection,
- product development thinking,
- self-employment exploration,
- motivation to return to suitable work,
- practical response to employment-support feedback.
