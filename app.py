import base64
import csv
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document
except Exception:
    Document = None

APP_NAME = "DigitLab Workout AI"
APP_TAGLINE = "Test version — health-aware workout planner"
BRAND_LINE = "by DigitLabCreative"
ASSETS_DIR = Path(__file__).parent / "assets"
LOGO = ASSETS_DIR / "digitlab_logo.png"
MARK = ASSETS_DIR / "digitlab_mark.png"
FEEDBACK_DIR = Path(__file__).parent / "feedback_data"
FEEDBACK_CSV = FEEDBACK_DIR / "feedback.csv"
SUPPORTED_FILE_TYPES = ["txt", "pdf", "docx"]


def img_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_header() -> None:
    if LOGO.exists():
        logo_b64 = img_to_base64(LOGO)
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:18px;padding:6px 0 18px 0;">
                <img src="data:image/png;base64,{logo_b64}" style="height:68px;width:auto;">
                <div>
                    <div style="font-size:2rem;font-weight:800;line-height:1.1;">{APP_NAME}</div>
                    <div style="font-size:1rem;color:#94A3B8;">{APP_TAGLINE}</div>
                    <div style="font-size:0.9rem;color:#64748B;">{BRAND_LINE}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title(APP_NAME)
        st.caption(APP_TAGLINE)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #070B18; color: #E5E7EB; }
        h1, h2, h3 { color: #E5E7EB; }
        section[data-testid="stSidebar"] { background-color: #020617; }
        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 14px;
        }
        .stButton>button {
            background: linear-gradient(90deg, #38BDF8, #8B5CF6);
            color: white;
            border-radius: 12px;
            border: 0;
            font-weight: 700;
        }
        .small-muted { color:#94A3B8; font-size:0.9rem; }
        .test-card {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            padding: 18px;
            margin: 8px 0 16px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("last_plan", None)
    st.session_state.setdefault("paywall_clicked", False)
    st.session_state.setdefault("feedback_saved", False)


def extract_text(uploaded_file) -> tuple[str, str]:
    if uploaded_file is None:
        return "", "none"
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".txt"):
        for enc in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
            try:
                return data.decode(enc), "txt"
            except UnicodeDecodeError:
                pass
        return data.decode("utf-8", errors="ignore"), "txt-fallback"
    if name.endswith(".pdf") and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages[:8]:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
            return "\n\n".join(pages), "pdf-text"
        except Exception as exc:
            return f"[Could not extract PDF text: {exc}]", "pdf-error"
    if name.endswith(".docx") and Document is not None:
        try:
            doc = Document(io.BytesIO(data))
            chunks = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(chunks), "docx"
        except Exception as exc:
            return f"[Could not extract DOCX text: {exc}]", "docx-error"
    return "", "unsupported"


def detect_health_flags(profile_text: str, docs_text: str) -> dict[str, Any]:
    text = f"{profile_text}\n{docs_text}".lower()
    flags = {
        "conditions": [],
        "pain_or_limitations": [],
        "red_flags": [],
        "recommended_intensity": "beginner / conservative",
        "medical_clearance_suggested": False,
    }

    condition_terms = {
        "back": "Back pain / spinal limitation",
        "sciatica": "Sciatica / nerve pain",
        "knee": "Knee pain / knee limitation",
        "hip": "Hip pain / mobility limitation",
        "shoulder": "Shoulder limitation",
        "asthma": "Asthma / breathing condition",
        "diabetes": "Diabetes",
        "blood pressure": "Blood pressure issue",
        "hypertension": "Hypertension",
        "heart": "Heart/cardiac history",
        "anxiety": "Anxiety/stress consideration",
        "depression": "Depression / low motivation consideration",
        "dizziness": "Dizziness / balance concern",
    }
    for term, label in condition_terms.items():
        if term in text and label not in flags["conditions"]:
            flags["conditions"].append(label)

    limitation_patterns = [
        (r"cannot stand|can't stand|standing", "Difficulty with standing tolerance"),
        (r"cannot walk|can't walk|walking|mobility", "Walking/mobility limitation"),
        (r"pain", "Pain may affect exercise selection"),
        (r"fatigue|tired", "Fatigue / reduced stamina"),
        (r"limited range|range of motion", "Reduced range of motion"),
    ]
    for pattern, label in limitation_patterns:
        if re.search(pattern, text) and label not in flags["pain_or_limitations"]:
            flags["pain_or_limitations"].append(label)

    red_terms = {
        "chest pain": "Chest pain mentioned — seek medical advice before exercise",
        "faint": "Fainting/faintness mentioned — seek medical advice before exercise",
        "shortness of breath": "Shortness of breath mentioned — keep intensity low and seek medical advice if unexplained",
        "recent surgery": "Recent surgery mentioned — medical clearance recommended",
        "dizziness": "Dizziness mentioned — avoid balance-risk exercises and seek medical advice if ongoing",
    }
    for term, label in red_terms.items():
        if term in text and label not in flags["red_flags"]:
            flags["red_flags"].append(label)

    if flags["red_flags"] or any("Heart" in c or "Blood pressure" in c or "Hypertension" in c for c in flags["conditions"]):
        flags["medical_clearance_suggested"] = True
        flags["recommended_intensity"] = "very low / medical clearance first"
    elif flags["conditions"] or flags["pain_or_limitations"]:
        flags["recommended_intensity"] = "low / conservative"

    return flags


def build_plan(age: int, goal: str, days: int, minutes: int, equipment: list[str], flags: dict[str, Any]) -> dict[str, Any]:
    low_impact = flags["conditions"] or flags["pain_or_limitations"]
    equipment_text = ", ".join(equipment) if equipment else "no equipment"
    plan_days = []
    focus_cycle = ["Mobility + full body", "Low-impact cardio", "Strength foundation", "Recovery mobility"]
    for i in range(days):
        focus = focus_cycle[i % len(focus_cycle)]
        if flags["medical_clearance_suggested"]:
            main = [
                "Do not start a new intense programme until medical advice is confirmed.",
                "Gentle walking or seated mobility only if already tolerated.",
                "Stop immediately if symptoms worsen.",
            ]
        elif low_impact:
            main = [
                "Sit-to-stand from chair — 2 sets of 6–8 slow reps",
                "Wall push-ups — 2 sets of 8–10 reps",
                "Supported step-back or heel raises — 2 sets of 8 reps each side",
                "Gentle walk or stationary bike — 5–12 minutes easy pace",
            ]
        else:
            main = [
                "Squat to comfortable depth — 3 sets of 8–10 reps",
                "Incline push-ups — 3 sets of 8–12 reps",
                "Hip hinge / Romanian deadlift pattern — 3 sets of 8 reps",
                "Easy cardio finisher — 8–15 minutes",
            ]
        plan_days.append(
            {
                "day": f"Day {i + 1}",
                "focus": focus,
                "duration": f"{minutes} minutes",
                "warmup": ["5 minutes easy movement", "Gentle joint circles", "Breathing reset"],
                "main": main,
                "cooldown": ["Gentle stretching", "Slow breathing", "Log pain/fatigue after session"],
            }
        )
    avoid = ["Sharp pain", "Sudden intensity jumps", "Exercises that aggravate known injury"]
    if flags["red_flags"]:
        avoid.insert(0, "Unsupervised moderate/high-intensity exercise until medically cleared")
    return {
        "summary": f"A conservative {days}-day plan for {goal}, using {equipment_text}. It is designed for testing feedback, not as medical advice.",
        "weekly_plan": plan_days,
        "avoid": avoid,
        "stop_if": ["Chest pain", "Dizziness", "Faintness", "Unusual shortness of breath", "Sharp or worsening pain"],
    }


def save_feedback(row: dict[str, Any]) -> None:
    FEEDBACK_DIR.mkdir(exist_ok=True)
    exists = FEEDBACK_CSV.exists()
    with FEEDBACK_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def render_feedback_form(context: str) -> None:
    st.markdown("---")
    st.subheader("Quick feedback")
    st.caption("This is the most important part of the test. Please be honest.")

    with st.form(f"feedback_form_{context}"):
        col1, col2 = st.columns(2)
        with col1:
            useful = st.radio("Would you use this again?", ["Yes", "Maybe", "No"], horizontal=True)
            clarity = st.slider("How clear is the plan?", 1, 5, 3)
            safety = st.slider("How safe/reasonable does it feel?", 1, 5, 3)
        with col2:
            pay = st.radio("Would you pay for a better version?", ["Yes", "Maybe", "No"], horizontal=True)
            price = st.selectbox("Best price point", ["£0", "£4.99", "£9.99", "£14.99", "£19.99", "Monthly subscription", "Not sure"])
            email = st.text_input("Email optional", placeholder="only if you want updates")
        biggest_issue = st.text_area("What should be improved first?", placeholder="Be specific: exercises, safety, UI, upload, export, mobile view...")
        submitted = st.form_submit_button("Submit feedback", use_container_width=True)

    if submitted:
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "useful": useful,
            "clarity_1_5": clarity,
            "safety_1_5": safety,
            "would_pay": pay,
            "price": price,
            "email": email,
            "improvement": biggest_issue,
        }
        save_feedback(row)
        st.session_state.feedback_saved = True
        st.success("Thanks — feedback saved for this test session.")

    if FEEDBACK_CSV.exists():
        st.download_button(
            "Download collected feedback CSV",
            data=FEEDBACK_CSV.read_bytes(),
            file_name="digitlab_workout_feedback.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_fake_paywall() -> None:
    st.markdown("---")
    st.markdown(
        """
        <div class="test-card">
        <h3>Test pricing signal</h3>
        <p class="small-muted">This button does not take payment. It only helps validate whether users would consider paying.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Unlock full personalised 4-week plan — £9.99", use_container_width=True):
        st.session_state.paywall_clicked = True
    if st.session_state.paywall_clicked:
        st.success("Test mode: payment is not enabled yet. Thanks — this click is a useful signal.")


def render_result(plan_bundle: dict[str, Any]) -> None:
    flags = plan_bundle["flags"]
    plan = plan_bundle["plan"]
    st.markdown("---")
    st.subheader("Your test result")
    c1, c2, c3 = st.columns(3)
    c1.metric("Recommended intensity", flags["recommended_intensity"])
    c2.metric("Medical clearance suggested", "Yes" if flags["medical_clearance_suggested"] else "No")
    c3.metric("Plan days", len(plan["weekly_plan"]))

    if flags["medical_clearance_suggested"]:
        st.warning("The app detected red flags or higher-risk health terms. This test version recommends medical clearance before starting anything new or intense.")
    else:
        st.info("This is a conservative test plan. Stop if symptoms worsen and seek professional advice where appropriate.")

    with st.expander("Detected health/safety flags", expanded=True):
        for label, key in [("Conditions", "conditions"), ("Pain or limitations", "pain_or_limitations"), ("Red flags", "red_flags")]:
            st.write(f"**{label}**")
            items = flags.get(key) or ["None detected"]
            for item in items:
                st.write(f"- {item}")

    st.markdown("### Plan summary")
    st.write(plan["summary"])
    st.markdown("### Weekly plan")
    for day in plan["weekly_plan"]:
        with st.expander(f"{day['day']} — {day['focus']}", expanded=False):
            st.write(f"**Duration:** {day['duration']}")
            for section in ["warmup", "main", "cooldown"]:
                st.write(f"**{section.title()}**")
                for item in day[section]:
                    st.write(f"- {item}")

    st.markdown("### Avoid / stop rules")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Avoid**")
        for item in plan["avoid"]:
            st.write(f"- {item}")
    with col2:
        st.write("**Stop if**")
        for item in plan["stop_if"]:
            st.write(f"- {item}")

    st.download_button(
        "Download test plan JSON",
        data=json.dumps(plan_bundle, indent=2),
        file_name="digitlab_workout_test_plan.json",
        mime="application/json",
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon=str(MARK) if MARK.exists() else "🏋️", layout="wide")
    inject_css()
    init_state()
    render_header()

    with st.sidebar:
        if MARK.exists():
            st.image(str(MARK), width=76)
        st.markdown("**Test mode**")
        st.caption("No login. No real payment. Built to collect early feedback.")
        st.markdown("---")
        st.write("**Testing goals**")
        st.write("1. Do the plans make sense?")
        st.write("2. Does safety screening help?")
        st.write("3. Would people pay?")

    tab_builder, tab_about, tab_feedback = st.tabs(["Generate test plan", "How to test", "Feedback log"])

    with tab_builder:
        st.markdown(
            """
            <div class="test-card">
            <b>Important:</b> This is an early test tool. It does not diagnose, treat, or replace medical, physiotherapy, or fitness advice.
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns([1.15, 0.85])
        with col1:
            name = st.text_input("Name optional", placeholder="Tester name")
            age = st.number_input("Age", min_value=12, max_value=100, value=35)
            goal = st.selectbox("Main goal", ["fat loss", "mobility", "general fitness", "strength foundation", "return to activity"])
            activity_level = st.selectbox("Current activity level", ["low", "moderate", "high"])
            days = st.slider("Training days per week", 1, 6, 3)
            minutes = st.slider("Session length", 10, 90, 30)
            equipment = st.multiselect("Available equipment", ["none", "chair", "bands", "dumbbells", "kettlebell", "bike", "treadmill", "mat"], default=["none"])
        with col2:
            health_issues = st.text_area("Health issues / injuries / limitations", height=110, placeholder="Example: knee pain, back pain, asthma, high blood pressure...")
            pain_areas = st.text_area("Pain areas or movements to avoid", height=90)
            notes = st.text_area("Anything else the plan should know?", height=90)
            upload = st.file_uploader("Optional: upload TXT/PDF/DOCX health or fitness note", type=SUPPORTED_FILE_TYPES)

        if st.button("Generate test workout plan", type="primary", use_container_width=True):
            docs_text, method = extract_text(upload) if upload else ("", "none")
            profile_text = f"Name: {name}\nAge: {age}\nGoal: {goal}\nActivity: {activity_level}\nHealth: {health_issues}\nPain: {pain_areas}\nNotes: {notes}"
            flags = detect_health_flags(profile_text, docs_text)
            plan = build_plan(int(age), goal, int(days), int(minutes), equipment, flags)
            st.session_state.last_plan = {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "profile": {
                    "name": name,
                    "age": age,
                    "goal": goal,
                    "activity_level": activity_level,
                    "days": days,
                    "minutes": minutes,
                    "equipment": equipment,
                },
                "document_extraction_method": method,
                "document_excerpt": docs_text[:900],
                "flags": flags,
                "plan": plan,
            }

        if st.session_state.last_plan:
            render_result(st.session_state.last_plan)
            render_fake_paywall()
            render_feedback_form("after_plan")

    with tab_about:
        st.subheader("Recommended test process")
        st.write("Use this version with 10–20 testers before building more features.")
        st.markdown(
            """
            **Ask testers:**
            1. Did the plan feel realistic?
            2. Did the safety warnings make sense?
            3. What was confusing?
            4. Would you use this again?
            5. Would you pay for a full 4-week version?
            """
        )
        st.subheader("What this test version intentionally does not include")
        st.write("No login, no Stripe, no database backend, no mobile app, no advanced AI coaching. The goal is fast validation.")

    with tab_feedback:
        st.subheader("Feedback collected in this environment")
        if FEEDBACK_CSV.exists():
            if pd is not None:
                st.dataframe(pd.read_csv(FEEDBACK_CSV), use_container_width=True)
            else:
                st.code(FEEDBACK_CSV.read_text(encoding="utf-8"))
            st.download_button("Download feedback CSV", FEEDBACK_CSV.read_bytes(), "digitlab_workout_feedback.csv", "text/csv")
        else:
            st.info("No feedback saved yet in this session/environment.")
        render_feedback_form("general")


if __name__ == "__main__":
    main()
