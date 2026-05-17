# DigitLab Workout AI — Test Version

This is a lightweight Streamlit-only test build for early user validation.

## Why this version exists
The original `workout_saas.zip` is a fuller local app with FastAPI backend, SQLite history, file processing and PDF/DOCX export. For public testing and feedback, that is too much friction.

This test version is designed for:
- sharing a public link,
- collecting quick feedback,
- validating whether the workout plan and safety screening feel useful,
- checking if users click a fake pricing button.

## What is included
- Branded DigitLab UI
- Simple workout plan generator
- Basic health/safety flag detection
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

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Create a GitHub repo, e.g. `digitlab-workout-ai-test`.
2. Upload these files:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `assets/digitlab_logo.png`
   - `assets/digitlab_mark.png`
3. Go to Streamlit Cloud.
4. Click **Deploy app**.
5. Select the repo and set main file to `app.py`.
6. Share the generated `streamlit.app` link with testers.

## Suggested tester message
```text
I’m testing an early AI workout planner. It creates a conservative workout plan and checks for basic health/safety flags.

It is not medical advice and payment is not active — I only want honest feedback.

Please test it here:
[LINK]

Questions:
1. Does the plan make sense?
2. Does it feel safe/reasonable?
3. What should be improved first?
4. Would you pay for a full 4-week version?
```

## Key metrics to watch
- How many people complete a plan
- How many click the fake paywall
- What price people select
- Common complaints in feedback
- Whether users say the plan feels safe and realistic
