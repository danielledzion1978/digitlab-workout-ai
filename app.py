import base64
import csv
import io
import json
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
APP_TAGLINE = "Test version — work-aware health and workout planner"
BRAND_LINE = "by DigitLabCreative"

APP_PUBLIC_URL = "https://diapp-workout-ai-ctr4uesmbtw4sho23kdwyw.streamlit.app/"
CONTACT_EMAIL = "danielledzion1978@googlemail.com"

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO = ASSETS_DIR / "digitlab_logo.png"
MARK = ASSETS_DIR / "digitlab_mark.png"

FEEDBACK_DIR = Path(__file__).parent / "feedback_data"
FEEDBACK_CSV = FEEDBACK_DIR / "feedback.csv"
SUPPORTED_FILE_TYPES = ["txt", "pdf", "docx"]


# -----------------------------
# Helpers
# -----------------------------

def img_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .safety-box {
            border: 1px solid rgba(255, 193, 7, 0.55);
            background: rgba(255, 193, 7, 0.10);
            padding: 1rem;
            border-radius: 0.75rem;
            margin: 0.5rem 0 1rem 0;
        }
        .small-muted { opacity: 0.75; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    if LOGO.exists():
        logo_b64 = img_to_base64(LOGO)
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:18px;padding:6px 0 14px 0;">
                <img src="data:image/png;base64,{logo_b64}" style="height:64px;width:auto;">
                <div>
                    <div style="font-size:2rem;font-weight:700;line-height:1.1;">{APP_NAME}</div>
                    <div style="font-size:1rem;opacity:0.9;">{APP_TAGLINE}</div>
                    <div style="font-size:0.9rem;opacity:0.7;">{BRAND_LINE}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title(APP_NAME)
        st.caption(f"{APP_TAGLINE} • {BRAND_LINE}")


def render_safety_disclaimer() -> None:
    st.warning(
        "Important: This app is for general fitness planning and early testing only. "
        "It is not medical advice and does not replace a qualified personal trainer, "
        "physiotherapist, GP, doctor, or other healthcare professional."
    )

    with st.expander("Read safety disclaimer before using this test app", expanded=False):
        st.markdown(
            """
            **DigitLab Workout AI is a prototype.** It provides general workout suggestions only.

            It does **not** provide medical advice, diagnosis, treatment, physiotherapy advice,
            rehabilitation advice, or a professional personal training service.

            Before starting a new workout plan, speak to a GP, physiotherapist, or qualified fitness
            professional if you:

            - are new to exercise;
            - have pain, injury, disability, or a medical condition;
            - are recovering from illness, surgery, or a recent accident;
            - have chest pain, dizziness, fainting, unusual shortness of breath, or heart/blood-pressure concerns;
            - are unsure whether exercise is safe for you.

            Stop exercising immediately if you feel chest pain, dizziness, faintness, severe shortness of breath,
            sharp pain, worsening pain, or any unusual symptoms.
            """
        )

    st.markdown(
        f"""
        <div class="small-muted">
        Public test link: <a href="{APP_PUBLIC_URL}" target="_blank">{APP_PUBLIC_URL}</a><br>
        Feedback/contact: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("last_plan", None)
    st.session_state.setdefault("paywall_clicked", False)
    st.session_state.setdefault("feedback_saved", False)


# -----------------------------
# File extraction
# -----------------------------

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


# -----------------------------
# Safety screening and plan logic
# -----------------------------

def detect_health_flags(profile_text: str, docs_text: str) -> dict[str, Any]:
    text = f"{profile_text}\n{docs_text}".lower()
    flags: dict[str, Any] = {
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
        "injury": "Injury mentioned",
        "pain": "Pain mentioned",
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

    higher_risk = any(
        "Heart" in c or "Blood pressure" in c or "Hypertension" in c
        for c in flags["conditions"]
    )

    if flags["red_flags"] or higher_risk:
        flags["medical_clearance_suggested"] = True
        flags["recommended_intensity"] = "very low / medical clearance first"
    elif flags["conditions"] or flags["pain_or_limitations"]:
        flags["recommended_intensity"] = "low / conservative"

    return flags


def build_work_guidance(work_profile: dict[str, Any]) -> dict[str, Any]:
    status = work_profile.get("status", "Not specified")
    work_type = work_profile.get("work_type", "Not specified")
    timing = work_profile.get("best_time", "Not specified")
    hours = work_profile.get("hours", "")
    barriers = work_profile.get("work_barriers", "")

    if timing == "before work":
        timing_note = "Keep this short and gentle: mobility, activation and breathing before leaving for work."
    elif timing == "during breaks":
        timing_note = "Use micro-sessions only: 2–5 minutes of standing, walking, stretching or breathing during breaks."
    elif timing == "after work":
        timing_note = "Use lower intensity after work if fatigue or pain is higher at the end of the day."
    elif timing == "rest days only":
        timing_note = "Avoid adding pressure on work days; place the main sessions on non-working days."
    else:
        timing_note = "Use the most realistic time of day and keep the plan easy to repeat."

    work_type_lower = work_type.lower()
    if "physical" in work_type_lower or any(word in work_type_lower for word in ["standing", "walking", "lifting"]):
        work_type_note = "Because the work pattern is physically active, avoid overloading legs/back after demanding shifts."
    elif "sedentary" in work_type_lower or "sitting" in work_type_lower:
        work_type_note = "Because the work pattern is mainly sedentary, include short movement breaks and posture changes."
    elif "mixed" in work_type_lower:
        work_type_note = "Because the work pattern is mixed, vary sessions depending on fatigue after each workday."
    else:
        work_type_note = "The plan should be adjusted if work duties are physically demanding or symptoms change."

    return {
        "status": status,
        "work_type": work_type,
        "working_hours": hours or "Not specified",
        "preferred_exercise_timing": timing,
        "work_barriers": barriers or "None provided",
        "timing_note": timing_note,
        "work_type_note": work_type_note,
    }


def build_plan(
    age: int,
    goal: str,
    days: int,
    minutes: int,
    equipment: list[str],
    flags: dict[str, Any],
    work_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    low_impact = bool(flags["conditions"] or flags["pain_or_limitations"])
    equipment_text = ", ".join(equipment) if equipment else "no equipment"
    work_guidance = build_work_guidance(work_profile or {})

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
                "work_fit": work_guidance["timing_note"],
                "warmup": ["5 minutes easy movement", "Gentle joint circles", "Breathing reset"],
                "main": main,
                "cooldown": ["Gentle stretching", "Slow breathing", "Log pain/fatigue after session"],
            }
        )

    avoid = ["Sharp pain", "Sudden intensity jumps", "Exercises that aggravate known injury"]
    if flags["red_flags"]:
        avoid.insert(0, "Unsupervised moderate/high-intensity exercise until medically cleared")

    return {
        "summary": (
            f"A conservative {days}-day plan for {goal}, using {equipment_text}. "
            "It also considers work routine and is designed for testing feedback, not as medical advice."
        ),
        "work_guidance": work_guidance,
        "weekly_plan": plan_days,
        "avoid": avoid,
        "stop_if": [
            "Chest pain",
            "Dizziness",
            "Faintness",
            "Unusual shortness of breath",
            "Sharp or worsening pain",
        ],
    }


# -----------------------------
# Feedback
# -----------------------------

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
            work_fit = st.slider("How well does it fit around work/daily routine?", 1, 5, 3)
        with col2:
            pay = st.radio("Would you pay for a better version?", ["Yes", "Maybe", "No"], horizontal=True)
            price = st.selectbox(
                "Best price point",
                ["£0", "£4.99", "£9.99", "£14.99", "£19.99", "Monthly subscription", "Not sure"],
            )
            email = st.text_input("Email optional", placeholder="only if you want updates")

        biggest_issue = st.text_area(
            "What should be improved first?",
            placeholder="Be specific: exercises, safety, UI, upload, export, mobile view...",
        )

        submitted = st.form_submit_button("Submit feedback", use_container_width=True)

    if submitted:
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "useful": useful,
            "clarity_1_5": clarity,
            "safety_1_5": safety,
            "work_fit_1_5": work_fit,
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
        ### Test pricing signal
        This button does not take payment. It only helps validate whether users would consider paying.
        """
    )

    if st.button("Unlock full personalised 4-week plan — £9.99", use_container_width=True):
        st.session_state.paywall_clicked = True

    if st.session_state.paywall_clicked:
        st.success("Test mode: payment is not enabled yet. Thanks — this click is a useful signal.")


# -----------------------------
# Rendering result
# -----------------------------

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
        st.warning(
            "The app detected red flags or higher-risk health terms. This test version recommends "
            "medical clearance before starting anything new or intense."
        )
    else:
        st.info("This is a conservative test plan. Stop if symptoms worsen and seek professional advice where appropriate.")

    with st.expander("Detected health/safety flags", expanded=True):
        for label, key in [
            ("Conditions", "conditions"),
            ("Pain or limitations", "pain_or_limitations"),
            ("Red flags", "red_flags"),
        ]:
            st.write(f"**{label}**")
            items = flags.get(key) or ["None detected"]
            for item in items:
                st.write(f"- {item}")

    st.markdown("### Plan summary")
    st.write(plan["summary"])

    if plan.get("work_guidance"):
        wg = plan["work_guidance"]
        st.markdown("### Work routine fit")
        st.write(f"**Work status:** {wg['status']}")
        st.write(f"**Work activity:** {wg['work_type']}")
        st.write(f"**Working hours / pattern:** {wg['working_hours']}")
        st.write(f"**Best exercise timing:** {wg['preferred_exercise_timing']}")
        st.info(wg["timing_note"])
        st.caption(wg["work_type_note"])

    st.markdown("### Weekly plan")
    for day in plan["weekly_plan"]:
        with st.expander(f"{day['day']} — {day['focus']}", expanded=False):
            st.write(f"**Duration:** {day['duration']}")
            if day.get("work_fit"):
                st.write(f"**Work-fit note:** {day['work_fit']}")
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


# -----------------------------
# Main app
# -----------------------------

def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=str(MARK) if MARK.exists() else "🏋️",
        layout="wide",
    )
    inject_css()
    init_state()
    render_header()
    render_safety_disclaimer()

    with st.sidebar:
        if MARK.exists():
            st.image(str(MARK), width=76)
        st.markdown("**Test mode**")
        st.caption("No login. No real payment. Built to collect early feedback.")
        st.markdown("---")
        st.write("**Testing goals**")
        st.write("1. Do the plans make sense?")
        st.write("2. Does safety screening help?")
        st.write("3. Does it fit around work?")
        st.write("4. Would people pay?")

    tab_builder, tab_about, tab_feedback = st.tabs(["Generate test plan", "How to test", "Feedback log"])

    with tab_builder:
        col1, col2 = st.columns([1.15, 0.85])

        with col1:
            name = st.text_input("Name optional", placeholder="Tester name")
            age = st.number_input("Age", min_value=12, max_value=100, value=35)
            goal = st.selectbox(
                "Main goal",
                ["fat loss", "mobility", "general fitness", "strength foundation", "return to activity"],
            )
            activity_level = st.selectbox("Current activity level", ["low", "moderate", "high"])
            days = st.slider("Training days per week", 1, 6, 3)
            minutes = st.slider("Session length", 10, 90, 30)
            equipment = st.multiselect(
                "Available equipment",
                ["none", "chair", "bands", "dumbbells", "kettlebell", "bike", "treadmill", "mat"],
                default=["none"],
            )

            st.markdown("### Work routine / employment support")
            work_status = st.selectbox(
                "Current work situation",
                ["working", "not working", "looking for work", "preparing to return to work", "student/training", "prefer not to say"],
            )
            work_type = st.selectbox(
                "Work activity type",
                [
                    "mainly sedentary/sitting",
                    "mainly standing",
                    "walking/mobile",
                    "physical/lifting",
                    "repetitive movement",
                    "mixed",
                    "not applicable",
                ],
            )
            work_hours = st.text_input(
                "Usual working hours or preferred pattern",
                placeholder="Example: 9–5, shifts, part-time mornings, flexible",
            )
            best_time = st.selectbox(
                "Most realistic time to exercise",
                ["before work", "during breaks", "after work", "rest days only", "flexible / not sure"],
            )

        with col2:
            st.markdown("### Safety check")
            beginner_warning = st.checkbox("I am a beginner or returning after a long break", value=False)
            has_health_issue = st.radio(
                "Do you currently have any injury, pain, medical condition, or movement limitation?",
                ["No", "Yes"],
                horizontal=True,
            )

            health_issues = st.text_area(
                "Health issues / injuries / limitations",
                height=110,
                placeholder="Example: knee pain, back pain, asthma, high blood pressure...",
            )
            pain_areas = st.text_area("Pain areas or movements to avoid", height=90)
            notes = st.text_area("Anything else the plan should know?", height=90)
            work_barriers = st.text_area(
                "Work-related barriers or adjustments",
                height=90,
                placeholder="Example: fatigue after shifts, standing tolerance, lifting, breaks, travel to work...",
            )
            upload = st.file_uploader(
                "Optional: upload TXT/PDF/DOCX health or fitness note",
                type=SUPPORTED_FILE_TYPES,
            )

            if beginner_warning:
                st.info("Beginner warning: start gently and consider asking a trainer to check your exercise technique.")

            if has_health_issue == "Yes":
                st.warning(
                    "Because you selected injury/pain/medical condition, this app will generate only a conservative plan. "
                    "Please consult a GP, physiotherapist, or qualified trainer before starting."
                )

            safety_acceptance = st.checkbox(
                "I understand this is not medical advice and does not replace a GP, physiotherapist, or personal trainer.",
                value=False,
            )

        if st.button("Generate test workout plan", type="primary", use_container_width=True):
            if not safety_acceptance:
                st.error("Please confirm the safety disclaimer before generating a plan.")
                st.stop()

            if has_health_issue == "Yes" and not (health_issues.strip() or pain_areas.strip()):
                st.error("Please briefly describe the injury, pain, medical condition, or limitation before generating a plan.")
                st.stop()

            docs_text, method = extract_text(upload) if upload else ("", "none")
            profile_text = (
                f"Name: {name}\n"
                f"Age: {age}\n"
                f"Goal: {goal}\n"
                f"Activity: {activity_level}\n"
                f"Beginner or returning after break: {beginner_warning}\n"
                f"Has injury/pain/medical condition: {has_health_issue}\n"
                f"Health: {health_issues}\n"
                f"Pain: {pain_areas}\n"
                f"Notes: {notes}"
            )

            work_profile = {
                "status": work_status,
                "work_type": work_type,
                "hours": work_hours,
                "best_time": best_time,
                "work_barriers": work_barriers,
            }

            flags = detect_health_flags(profile_text, docs_text)
            if beginner_warning and "Beginner / returning after a long break" not in flags["conditions"]:
                flags["conditions"].append("Beginner / returning after a long break")
                if not flags["medical_clearance_suggested"]:
                    flags["recommended_intensity"] = "beginner / conservative"

            plan = build_plan(
                age=int(age),
                goal=goal,
                days=int(days),
                minutes=int(minutes),
                equipment=equipment,
                flags=flags,
                work_profile=work_profile,
            )

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
                    "beginner_or_returning": beginner_warning,
                    "has_health_issue": has_health_issue,
                    "work_profile": work_profile,
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
            3. Did the plan fit around work, shifts or daily routine?
            4. What was confusing?
            5. Would you use this again?
            6. Would you pay for a full 4-week version?
            """
        )
        st.subheader("What this test version intentionally does not include")
        st.write(
            "No login, no Stripe, no database backend, no mobile app, no advanced AI coaching. "
            "The goal is fast validation."
        )

    with tab_feedback:
        st.subheader("Feedback collected in this environment")
        if FEEDBACK_CSV.exists():
            if pd is not None:
                st.dataframe(pd.read_csv(FEEDBACK_CSV), use_container_width=True)
            else:
                st.code(FEEDBACK_CSV.read_text(encoding="utf-8"))
            st.download_button(
                "Download feedback CSV",
                FEEDBACK_CSV.read_bytes(),
                "digitlab_workout_feedback.csv",
                "text/csv",
            )
        else:
            st.info("No feedback saved yet in this session/environment.")

        render_feedback_form("general")


if __name__ == "__main__":
    main()
