import html
import os
import sys
import time

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    for setting in ("LLM_BACKEND", "LLM_MODEL", "OPENAI_API_KEY", "OPENAI_MODEL", "OLLAMA_MODEL"):
        if setting not in os.environ and setting in st.secrets:
            os.environ[setting] = str(st.secrets[setting])
except StreamlitSecretNotFoundError:
    pass

os.environ.setdefault("LLM_BACKEND", "openai" if os.getenv("OPENAI_API_KEY") else "mock")

from core.config import AppConfig
from core.debate_engine import MAX_ROUNDS, MIN_ROUNDS, run_debate
from core.reporting import build_debate_report, export_report
from utils.llm_model.llm import (
    get_active_backend,
    get_active_model,
    get_model_options_for_backend,
    set_active_backend,
)

st.set_page_config(
    page_title=AppConfig.app_title,
    page_icon="⚖️",
    layout="wide",
)

TOPIC_PLACEHOLDER = "Example: Will AI replace the majority of white-collar jobs?"


st.markdown(
    f"""
    <style>
        :root {{
            --bg: #0b1220;
            --panel: #111b2b;
            --panel-alt: #16233a;
            --border: rgba(148, 163, 184, 0.18);
            --text: #e5eefb;
            --muted: #b2c1d9;
            --pro: #1d4ed8;
            --pro-soft: rgba(29, 78, 216, 0.18);
            --against: #b91c1c;
            --against-soft: rgba(185, 28, 28, 0.18);
            --success: #0f766e;
            --warning: #f59e0b;
            --shadow: 0 25px 50px rgba(15, 23, 42, 0.25);
        }}
        .stApp {{
            background: linear-gradient(180deg, #09111d 0%, #0f172a 100%);
            color: var(--text);
        }}
        .main .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        .hero {{
            background: linear-gradient(135deg, rgba(30, 64, 175, 0.14), rgba(14, 116, 144, 0.18));
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.5rem 1.75rem;
            box-shadow: var(--shadow);
            margin-bottom: 1.4rem;
        }}
        .title {{
            font-size: 2.4rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
        }}
        .subtitle {{
            color: var(--muted);
            font-size: 1rem;
            margin-top: 0.35rem;
        }}
        .metric-card {{
            background: rgba(17, 27, 43, 0.88);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            box-shadow: var(--shadow);
            height: 100%;
        }}
        .metric-label {{
            color: var(--muted);
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .metric-value {{
            font-size: 1.55rem;
            font-weight: 800;
            margin-top: 0.35rem;
        }}
        .panel {{
            background: rgba(17, 27, 43, 0.86);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            margin-top: 1rem;
        }}
        .chat-pro {{
            background: linear-gradient(135deg, rgba(29, 78, 216, 0.15), rgba(30, 64, 175, 0.08));
            border: 1px solid rgba(96, 165, 250, 0.28);
            border-left: 5px solid var(--pro);
            padding: 0.95rem 1rem;
            border-radius: 12px;
            margin: 0.75rem 0;
            color: var(--text);
        }}
        .chat-against {{
            background: linear-gradient(135deg, rgba(185, 28, 28, 0.12), rgba(127, 29, 29, 0.08));
            border: 1px solid rgba(248, 113, 113, 0.28);
            border-left: 5px solid var(--against);
            padding: 0.95rem 1rem;
            border-radius: 12px;
            margin: 0.75rem 0;
            color: var(--text);
        }}
        .status-pill {{
            display: inline-block;
            background: rgba(15, 118, 110, 0.14);
            border: 1px solid rgba(45, 212, 191, 0.28);
            color: #c7f9f2;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        [data-testid="stSidebar"] {{
            background: rgba(9, 17, 29, 0.9);
        }}
        .stButton > button {{
            width: 100%;
            background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 700;
            padding: 0.7rem 1rem;
        }}
        .stButton > button:hover {{
            background: linear-gradient(135deg, #1d4ed8 0%, #0284c7 100%);
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    f"""
    <div class="hero">
        <div class="status-pill">Enterprise Debate Studio</div>
        <div class="title">{AppConfig.app_name}</div>
        <div class="subtitle">AI-powered multi-agent argument analysis with evidence-backed reasoning.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Debate Controls")
    topic = st.text_input("Debate Topic", placeholder=TOPIC_PLACEHOLDER, value="")
    rounds = st.slider("Rounds", min_value=MIN_ROUNDS, max_value=MAX_ROUNDS, value=2, step=1)

    backend_options = ["ollama", "mock"]
    try:
        import openai  # noqa: F401
        backend_options.append("openai")
    except ImportError:
        pass

    selected_backend = st.selectbox(
        "Model Backend",
        options=backend_options,
        index=backend_options.index(get_active_backend()) if get_active_backend() in backend_options else 0,
    )
    model_options = get_model_options_for_backend(selected_backend)
    model_name = st.selectbox(
        "Model Name",
        options=model_options,
        index=model_options.index(get_active_model()) if get_active_model() in model_options else 0,
    )
    start = st.button("Launch Debate", use_container_width=True)

    st.markdown("---")
    st.caption("System")
    st.write(f"Model: {model_name}")
    st.write(f"Backend: {selected_backend}")
    st.write(f"Version: {AppConfig.version}")


metric_cols = st.columns(4)
with metric_cols[0]:
    st.markdown("<div class='metric-card'><div class='metric-label'>Rounds</div><div class='metric-value'>1–10</div></div>", unsafe_allow_html=True)
with metric_cols[1]:
    st.markdown("<div class='metric-card'><div class='metric-label'>Judging</div><div class='metric-value'>Structured</div></div>", unsafe_allow_html=True)
with metric_cols[2]:
    st.markdown("<div class='metric-card'><div class='metric-label'>Evidence</div><div class='metric-value'>Wikipedia</div></div>", unsafe_allow_html=True)
with metric_cols[3]:
    st.markdown("<div class='metric-card'><div class='metric-label'>Status</div><div class='metric-value'>Ready</div></div>", unsafe_allow_html=True)


def stream_text(text, css_class):
    box = st.empty()
    content = ""
    for char in text:
        content += char
        box.markdown(
            f"<div class='{css_class}'>{html.escape(content)}</div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.01)


def stream_debate(topic_value, round_count):
    try:
        yield from run_debate(topic_value, round_count)
    except (RuntimeError, ValueError) as exc:
        st.error(f"Unable to run debate: {exc}")


if start:
    set_active_backend(selected_backend, model_name)

    if not topic.strip():
        st.warning("Please enter a valid debate topic before launching.")
    else:
        st.markdown("<div class='panel'><h3 style='margin:0;'>Live Debate</h3></div>", unsafe_allow_html=True)

        evidence_data = []
        transcript = []

        for step, data in stream_debate(topic, rounds):
            if step == "evidence":
                evidence_data = data
                st.markdown("### Evidence Base")
                evidence_cols = st.columns(min(len(data), 3))
                for idx, source in enumerate(data[:3]):
                    with evidence_cols[idx % len(evidence_cols)]:
                        st.markdown(
                            f"""
                            <div class='metric-card'>
                                <div class='metric-label'>{source['id']}</div>
                                <div style='font-weight:700; margin-top:0.5rem;'>{source['title']}</div>
                                <div style='color:#b2c1d9; font-size:0.9rem; margin-top:0.5rem;'>{source['excerpt']}</div>
                                <div style='margin-top:0.7rem;'><a href='{source['url']}' target='_blank' rel='noreferrer'>Open source</a></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            elif step.startswith("round_"):
                round_num = int(step.split('_')[-1])
                transcript.append({"round": round_num, "pro": data["pro"], "against": data["against"]})
                st.markdown(f"### Round {round_num}")
                pro_col, against_col = st.columns(2)

                with pro_col:
                    with st.spinner("Pro agent is preparing..."):
                        time.sleep(0.25)
                    stream_text(f"Pro: {data['pro']}", "chat-pro")

                with against_col:
                    with st.spinner("Against agent is preparing..."):
                        time.sleep(0.25)
                    stream_text(f"Against: {data['against']}", "chat-against")

            elif step == "judge":
                st.markdown("---")
                st.markdown("## Final Decision")
                winner = data["winner"]
                reason = data["reason"]
                scores = data["scores"]

                if winner.lower() == "pro":
                    st.success(f"Winner: {winner}")
                else:
                    st.error(f"Winner: {winner}")

                summary_cols = st.columns(3)
                with summary_cols[0]:
                    st.metric("Pro Total", sum(scores["pro"].values()))
                with summary_cols[1]:
                    st.metric("Against Total", sum(scores["against"].values()))
                with summary_cols[2]:
                    st.metric("Decision", winner)

                st.markdown("### Judge rationale")
                stream_text(reason, "chat-pro")

                st.markdown("### Score Breakdown")
                score_df = pd.DataFrame(
                    {
                        "Criteria": ["Logic", "Clarity", "Examples"],
                        "Pro": [
                            scores["pro"]["logic"],
                            scores["pro"]["clarity"],
                            scores["pro"]["examples"],
                        ],
                        "Against": [
                            scores["against"]["logic"],
                            scores["against"]["clarity"],
                            scores["against"]["examples"],
                        ],
                    }
                )

                st.bar_chart(score_df.set_index("Criteria"), height=240)

                pro_total = score_df["Pro"].sum()
                against_total = score_df["Against"].sum()

                def highlight_winner(value, column_name):
                    if column_name == "Pro" and pro_total > against_total:
                        return "background-color: rgba(29, 78, 216, 0.18); color: white;"
                    if column_name == "Against" and against_total > pro_total:
                        return "background-color: rgba(185, 28, 28, 0.18); color: white;"
                    return ""

                styled_df = score_df.style.apply(
                    lambda col: [highlight_winner(v, col.name) for v in col],
                    axis=0,
                )
                st.dataframe(styled_df, use_container_width=True)

                if "supporting_quotes" in data:
                    st.markdown("### Supporting Quotes")
                    for item in data["supporting_quotes"]:
                        icon = "🟦" if item["side"] == "Pro" else "🟥"
                        st.markdown(f"{icon} <b>{item['side']}</b>: {html.escape(item['quote'])}", unsafe_allow_html=True)

                report = build_debate_report(topic, rounds, evidence_data, data, transcript)
                json_report = export_report(report, file_format="json")
                csv_report = export_report(report, file_format="csv")

                st.markdown("### Export Debate Report")
                export_cols = st.columns(2)
                with export_cols[0]:
                    st.download_button(
                        label="Download JSON",
                        data=json_report,
                        file_name=f"debate-report-{topic.lower().replace(' ', '-')}.json",
                        mime="application/json",
                    )
                with export_cols[1]:
                    st.download_button(
                        label="Download CSV",
                        data=csv_report,
                        file_name=f"debate-report-{topic.lower().replace(' ', '-')}.csv",
                        mime="text/csv",
                    )

                break

else:
    st.info("Enter a debate topic and click Launch Debate to generate a structured multi-agent evaluation.")